import psycopg
from asyncio import gather


class IdeasTables:
    async def add_idea(self, line):
        """
        Adds a new idea to the database

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
        mentor_id = (await self.get_mentors(chat_id=line['chat_id']))[0]['id']
        work = (await (await self.db.execute('INSERT INTO IDEAS VALUES('
                                             'DEFAULT, %s, %s) '
                                             'RETURNING ID',
                                             (mentor_id, line['description'],))).fetchone())[0]
        await gather(*[self.db.execute('INSERT INTO IDEAS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING', (work, subj,))
                       for subj in line['subjects']])
        await self.db.commit()
        return work

    async def assemble_ideas_dict(self, cursor):
        list = []
        for i in cursor:
            if i is None:
                continue
            line = {
                'id': i[0],
                'mentor': i[1],
                'subjects': await self.get_subjects(work_id=i[0]),
                'description': i[2],
            }
            list.append(line)
        return list

    async def get_ideas(self, id_field=None, subjects=[], mentor=None):
        """
        Gets all submitted ideas that satisfy the argument subject
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
            res = [await (await self.db.execute('SELECT * FROM IDEAS '
                                                'WHERE ID = %s', (id_field,))).fetchone()]
            return await self.assemble_ideas_dict(res)
        if subjects:
            ids = await (await self.db.execute('SELECT IDEA FROM IDEAS_SUBJECTS '
                                               'WHERE SUBJECT = ANY(%s)', (subjects,))).fetchall()
            works = [await (await self.db.execute('SELECT * FROM IDEAS '
                                                  'WHERE ID = %s', (id_f,))).fetchone()
                     for (id_f,) in ids]
            return await self.assemble_ideas_dict(works)
        if mentor is not None:
            res = await (await self.db.execute('SELECT * FROM IDEAS '
                                               'WHERE MENTOR = %s',
                                               (mentor,))).fetchall()
            return await self.assemble_ideas_dict(res)
        res = await (await self.db.execute('SELECT * FROM IDEAS')).fetchall()
        return await self.assemble_ideas_dict(res)

    async def modify_idea(self, line):
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
        old_ids = await (await self.db.execute('SELECT SUBJECT FROM IDEAS_SUBJECTS '
                                               'WHERE IDEA = %(id)s',
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
        await gather(self.db.execute('UPDATE IDEAS SET '
                                     'DESCRIPTION = %s '
                                     'WHERE ID = %s',
                                     (line['description'], line['id'],)),
                     self.db.execute('DELETE FROM IDEAS_SUBJECTS '
                                     'WHERE IDEA = %s', (line['id'],)))
        await gather(*[self.db.execute('INSERT INTO IDEAS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING',
                                       (line['id'], subj,))
                       for subj in subjects])
        await self.db.commit()

    async def remove_idea(self, id_field):
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
        await self.db.execute('DELETE FROM IDEAS_SUBJECTS '
                              'WHERE IDEA = %s', (id_field,))
        await self.db.execute('DELETE FROM IDEAS '
                              'WHERE ID = %s', (id_field,))
        await self.db.commit()
