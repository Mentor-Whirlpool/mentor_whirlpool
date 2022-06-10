import psycopg
from asyncio import gather


class StudentTables():
    async def assemble_students_dict(self, cursor):
        list = []
        for i in cursor:
            if i is None:
                continue
            line = {
                'id': i[0],
                'name': i[1],
                'chat_id': i[2],
                'course_works': (await self.get_course_works(student=i[0]) +
                                 await self.get_accepted(student=i[0])),
            }
            list.append(line)
        return list

    async def get_students(self, id_field=None, chat_id=None, mentor_id=None):
        """
        If any arguments are supplied, they are used as a key to find
        a specific student. Otherwise, fetches all students from the database

        Parameters
        ----------
        id_field : int
            Database ID of specified student
        chat_id : int
            Telegram chat ID of specified student
        mentor_id : int
            Database ID of a mentor from which to get the students
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        values = []
        if id_field is not None:
            values = await self.db.execute('SELECT * FROM STUDENTS '
                                           'WHERE ID = %s', (id_field,))
            return await self.assemble_students_dict(await values.fetchall())
        if chat_id is not None:
            values = await self.db.execute('SELECT * FROM STUDENTS '
                                           'WHERE CHAT_ID = %s', (chat_id,))
            return await self.assemble_students_dict(await values.fetchall())
        if mentor_id is not None:
            ids = await (await self.db.execute('SELECT STUDENT FROM MENTORS_STUDENTS WHERE '
                                               'MENTOR = %s', (mentor_id,))).fetchall()
            if ids is None:
                return []
            cursors = await gather(*[self.db.execute('SELECT * FROM STUDENTS '
                                                     'WHERE ID = %s', (id_f,))
                                     for (id_f,) in ids])
            return await self.assemble_students_dict(await gather(*[curs.fetchone()
                                                                    for curs in cursors]))
        return await self.assemble_students_dict(
            await (await self.db.execute('SELECT * FROM STUDENTS')).fetchall()
        )

    async def remove_student(self, id_field):
        """
        Removes a line from COURSE_WORKS table
        Removing a course work decrements COUNT column in SUBJECTS table

        Parameters
        ----------
        id_field : int
            The first column of the table

        Raises
        ------
        DBAccessError whatever
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        course_works = await (await self.db.execute('SELECT ID FROM COURSE_WORKS '
                                                    'WHERE STUDENT = %s', (id_field,))).fetchall()
        accepted = await (await self.db.execute('SELECT ID FROM ACCEPTED '
                                                'WHERE STUDENT = %s', (id_field,))).fetchall()
        await gather(self.db.execute('DELETE FROM MENTORS_STUDENTS '
                                     'WHERE STUDENT = %s', (id_field,)),
                     *[self.db.execute('DELETE FROM COURSE_WORKS_SUBJECTS '
                                       'WHERE COURSE_WORK = %s', (cw_id,))
                       for (cw_id,) in course_works],
                     *[self.db.execute('DELETE FROM ACCEPTED_SUBJECTS '
                                       'WHERE COURSE_WORK = %s', (cw_id,))
                       for (cw_id,) in accepted])
        await gather(self.db.execute('DELETE FROM COURSE_WORKS '
                                     'WHERE STUDENT = %s', (id_field,)),
                     self.db.execute('DELETE FROM ACCEPTED '
                                     'WHERE STUDENT = %s', (id_field,)),
                     self.db.execute('DELETE FROM STUDENTS '
                                     'WHERE ID = %s', (id_field,)))
        await self.db.commit()

