import psycopg
from asyncio import gather


class CourseWorksTables:
    async def add_course_work(self, line):
        """
        Adds a new course work to the database
        Adding a course work increments COUNT column in SUBJECTS table

        Parameters
        ----------
        line : dict
            Dict with field names 'name', 'chat_id', 'subjects', 'description'

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists

        Returns
        -------
        int
            Database ID of inserted course work
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('INSERT INTO STUDENTS VALUES('
                              'DEFAULT, %(name)s, %(chat_id)s) '
                              'ON CONFLICT (CHAT_ID) DO NOTHING',
                              line)
        # need to do it separately, otherwise fetchone will hang the runtime on
        # database not returning anything
        stud_id = (await self.get_students(chat_id=line['chat_id']))[0]['id']
        work = (await (await self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                                             'DEFAULT, %s, %s) '
                                             'RETURNING ID',
                                             (stud_id, line['description'],))).fetchone())[0]
        await gather(*[self.db.execute('INSERT INTO COURSE_WORKS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING', (work, subj,))
                       for subj in line['subjects']])
        await self.db.commit()
        return work

    async def assemble_courses_dict(self, cursor):
        list = []
        for i in cursor:
            if i is None:
                continue
            line = {
                'id': i[0],
                'student': i[1],
                'subjects': await self.get_subjects(work_id=i[0]),
                'description': i[2],
            }
            list.append(line)
        return list

    async def get_course_works(self, id_field=None, subjects=[], student=None):
        """
        Gets all submitted course works that satisfy the argument subject
        Subject may be empty, in this case, return all course works

        Parameters
        ----------
        subjects : iterable(integer)
            All database ids, indicating needed subjects
            If empty, consider all possible subjects needed

        Raises
        ------
        DBAccessError whatever

        Returns
        ------
        iterable
            Iterable over all compliant lines (dict of columns excluding ID)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if id_field is not None:
            res = [await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                                'WHERE ID = %s', (id_field,))).fetchone()]
            return await self.assemble_courses_dict(res)
        if subjects:
            ids = await (await self.db.execute('SELECT COURSE_WORK FROM COURSE_WORKS_SUBJECTS '
                                               'WHERE SUBJECT = ANY(%s)', (subjects,))).fetchall()
            ids += await (await self.db.execute('SELECT COURSE_WORK FROM ACCEPTED_SUBJECTS '
                                                'WHERE SUBJECT = ANY(%s)', (subjects,))).fetchall()
            ids = set(ids)
            works = [await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                                  'WHERE ID = %s', (id_f,))).fetchone()
                     for (id_f,) in ids]
            return await self.assemble_courses_dict(works)
        if student is not None:
            res = await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                               'WHERE STUDENT = %s',
                                               (student,))).fetchall()
            return await self.assemble_courses_dict(res)
        res = await (await self.db.execute('SELECT * FROM COURSE_WORKS')).fetchall()
        return await self.assemble_courses_dict(res)

    async def modify_course_work(self, line):
        """
        Modifies an existing line in the database, matching 'chat_id' field
        Modifying a course work may update SUBJECTS table if subject is changed

        Parameters
        ----------
        line : dict
            Dict field names are 'id': int, 'subjects': str[], 'description': str

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        old_ids = await (await self.db.execute('SELECT SUBJECT FROM COURSE_WORKS_SUBJECTS '
                                               'WHERE COURSE_WORK = %(id)s',
                                               line)).fetchall()
        old = [subj for (subj,) in
               [await (await self.db.execute('SELECT SUBJECT FROM SUBJECTS '
                                             'WHERE ID = %s', (id_f,))).fetchone()
                for (id_f,) in old_ids]]
        tasks = []
        for new in set(line['subjects']).difference(old):
            tasks.append(self.add_subject(new))
        for removed in set(old).difference(line['subjects']):
            tasks.append(self.db.execute('UPDATE SUBJECTS '
                                         'SET COUNT = COUNT - 1 '
                                         'WHERE SUBJECT = %s', (removed,)))
        await gather(*tasks)
        subjects = [id_f for (id_f,) in
                    [await (await self.db.execute('SELECT ID FROM SUBJECTS '
                                                  'WHERE SUBJECT = %s',
                                                  (subj,))).fetchone()
                     for subj in line['subjects']]]
        await gather(self.db.execute('UPDATE COURSE_WORKS SET '
                                     'DESCRIPTION = %s '
                                     'WHERE ID = %s',
                                     (line['description'], line['id'],)),
                     self.db.execute('DELETE FROM COURSE_WORKS_SUBJECTS '
                                     'WHERE COURSE_WORK = %s', (line['id'],)))
        await gather(*[self.db.execute('INSERT INTO COURSE_WORKS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING',
                                       (line['id'], subj,))
                       for subj in subjects])
        await self.db.commit()

    async def remove_course_work(self, id_field):
        """
        Removes a line from COURSE_WORKS table
        Removing a course work decrements COUNT column in SUBJECTS table

        Parameters
        ----------
        id_field : int
            Database ID of course work

        Raises
        ------
        DBAccessError whatever
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        (stud_id,) = await (await self.db.execute('SELECT STUDENT FROM COURSE_WORKS '
                                                  'WHERE ID = %s', (id_field,))).fetchone()
        await self.db.execute('DELETE FROM COURSE_WORKS_SUBJECTS '
                              'WHERE COURSE_WORK = %s', (id_field,))
        await self.db.execute('DELETE FROM COURSE_WORKS '
                              'WHERE ID = %s', (id_field,))
        student_relevant = ((await (await self.db.execute('SELECT EXISTS('
                                                          'SELECT * FROM COURSE_WORKS '
                                                          'WHERE STUDENT = %s)',
                                                          (stud_id,))).fetchone())[0] or
                            (await (await self.db.execute('SELECT EXISTS('
                                                          'SELECT * FROM ACCEPTED '
                                                          'WHERE STUDENT = %s)',
                                                          (stud_id,))).fetchone())[0])
        if not student_relevant:
            await self.db.execute('DELETE FROM STUDENTS '
                                  'WHERE ID = %s', (stud_id,))
        await self.db.commit()
