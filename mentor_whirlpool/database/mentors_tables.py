import psycopg
from asyncio import gather


class MentorsTables:
    async def add_mentor(self, line):
        """
        Adds a new mentor to the database

        Parameters
        ----------
        line : dict
            dict with fields 'name', 'chat_id', 'subjects'

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        (ment_id,) = await (await self.db.execute('INSERT INTO MENTORS VALUES('
                                                  'DEFAULT, %(name)s, %(chat_id)s, 0) '
                                                  'RETURNING ID', line)).fetchone()
        subj_ids = []
        if line['subjects'] is not None:
            subj_ids = await gather(*[self.add_subject(subj) for subj in line['subjects']])
        await gather(*[self.db.execute('INSERT INTO MENTORS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING',
                                       (ment_id, subj,)) for subj in subj_ids])
        await self.db.commit()

    async def assemble_mentors_dict(self, cursor):
        list = []
        for i in cursor:
            if i is None:
                continue
            students = await self.get_students(mentor_id=i[0])
            line = {
                'id': i[0],
                'name': i[1],
                'chat_id': i[2],
                'subjects': await self.get_subjects(mentor_id=i[0]),
                'load': i[3],
                'students': students,
            }
            list.append(line)
        return list

    async def get_mentors(self, id=None, chat_id=None, student=None):
        """
        Gets all lines from MENTORS table
        If student argument is supplied, search for a mentor for a specific
        student

        Parameters
        ----------
        id : int
            database id of the mentor
        chat_id : int
            telegram chat_id of required mentor
        student : int
            database id of student to search mentor by

        Returns
        ------
        iterable
            Iterable over all mentors
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        mentors = None
        if id is not None:
            mentors = [await (await self.db.execute('SELECT * FROM MENTORS '
                                                    'WHERE ID = %s',
                                                    (id,))).fetchone()]
        if chat_id is not None:
            mentors = [await (await self.db.execute('SELECT * FROM MENTORS '
                                                    'WHERE CHAT_ID = %s',
                                                    (chat_id,))).fetchone()]
        if student is not None:
            mentor = await (await self.db.execute('SELECT MENTOR FROM MENTORS_STUDENTS '
                                                  'WHERE STUDENT= %s',
                                                  (student,))).fetchone()
            if mentor is None:
                return []
            # parameter is just mentor, as it is already a tuple
            # beneficial to do so, because fetchone will return None if
            # mentor has not been found
            mentors = [await (await self.db.execute('SELECT * FROM MENTORS '
                                                    'WHERE ID = %s',
                                                    mentor)).fetchone()]
        if id is None and chat_id is None and student is None:
            mentors = await (await self.db.execute('SELECT * FROM MENTORS')).fetchall()
        return await self.assemble_mentors_dict(mentors)

    async def check_is_mentor(self, chat_id):
        """
        Checks if specified chat_id is present in database as a mentor

        Parameters
        ----------
        chat_id : int
            a chat id to check

        Returns
        -------
        boolean
            True if exists, false otherwise
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        return (await (await self.db.execute('SELECT EXISTS('
                                             'SELECT * FROM MENTORS '
                                             'WHERE CHAT_ID = %s)',
                                             (chat_id,))).fetchone())[0]

    async def remove_mentor(self, id_field=None, chat_id=None):
        """
        Removes a line from MENTORS table

        Parameters
        ----------
        id_field : int
            database id of the mentor to delete
        chat_id : int
            telegram chat_id of mentor to delete

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if chat_id is not None:
            (id_field,) = await (await self.db.execute('SELECT ID FROM MENTORS '
                                                'WHERE CHAT_ID = %s', (chat_id,))
                                 ).fetchone()
        students = await (await self.db.execute('SELECT STUDENT FROM MENTORS_STUDENTS '
                                                'WHERE MENTOR = %s', (id_field,))).fetchall()

        await gather(self.db.execute('DELETE FROM MENTORS_SUBJECTS '
                                     'WHERE MENTOR = %s', (id_field,)),
                     self.db.execute('DELETE FROM MENTORS_STUDENTS '
                                     'WHERE MENTOR = %s', (id_field,)),
                     self.db.execute('DELETE FROM MENTORS '
                                     'WHERE ID = %s', (id_field,)),
                     *[self.reject_student(id_field, stud)
                       for (stud,) in students])
        await self.db.commit()

    async def add_mentor_subjects(self, id_field, subjects):
        """
        Add subjects to mentor

        Parameters
        ----------
        id_field : int
            ID (not chat_id) of mentor to edit
        subjects : iterable(str)
            Strings of subjects

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        subj_ids = await gather(*[self.add_subject(subj) for subj in subjects])
        await gather(*[self.db.execute('INSERT INTO MENTORS_SUBJECTS VALUES('
                                       '%s, %s)', (id_field, subj,)) 
                       for subj in subj_ids])
        await self.db.commit()

    async def remove_mentor_subjects(self, id_field, subjects):
        """
        Removes a string from SUBJECTS array of a mentor with a specified ID

        Parameters
        ----------
        id_field : int
            ID (not chat_id) of mentor to edit
        subjects : iterable(str)
            strings of subject

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        subj_ids = [await (await self.db.execute('SELECT ID FROM SUBJECTS '
                                                 'WHERE SUBJECT = %s',
                                                 (subj,))).fetchone()
                    for subj in subjects]
        await gather(*[self.db.execute('DELETE FROM MENTORS_SUBJECTS '
                                       'WHERE MENTOR = %s AND '
                                       'SUBJECT = %s', (id_field, subj,))
                       for (subj,) in subj_ids])
        await self.db.commit()
