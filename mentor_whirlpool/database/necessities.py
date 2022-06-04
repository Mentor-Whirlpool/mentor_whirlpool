import psycopg
from asyncio import gather


class Database:
    # init
    def __init__(self):
        self.db = None
        self.conn_opts = ('dbname=mentor_whirlpool '
                          'user=postgres '
                          'host=localhost '
                          'port=5432 '
                          'password=s3cret')

    async def initdb(self):
        """
        Creates database model if not declared already
        this is generally achieved with SQL's CREATE TABLE IF NOT EXISTS
        don't really care if it returns success
        as it is so essential, someone will notice eventually
            Structure shall be as follows:
                Table "STUDENTS":
        ID(PRIMARY KEY) | NAME(TEXT NOT NULL) |
        CHAT_ID(BIGINT NOT NULL UNIQUE) | COURSE_WORKS (BIGINT)
                Table "COURSE_WORKS":
        ID(PRIMARY KEY) | STUDENT(BIGINT NOT NULL) |
        SUBJECTS(TEXT[] NOT NULL) | DESCRIPTION(TEXT)
                Table "ACCEPTED":
        ID(PRIMARY KEY) | STUDENT(BIGINT NOT NULL UNIQUE) |
        SUBJECTS(TEXT[] NOT NULL) | DESCRIPTION(TEXT)
                Table "SUBJECTS":
        ID(PRIMARY KEY) | SUBJECT(TEXT NOT NULL) | COUNT(INT)
                Table "MENTORS":
        ID(PRIMARY KEY) | NAME(TEXT NOT NULL) |
        CHAT_ID(BIGINT NOT NULL) | SUBJECTS(TEXT[]) |
        LOAD(INT) | STUDENTS (BIGINT[])
                Table "ADMINS":
        ID(PRIMARY KEY) | CHAT_ID (BIGINT NOT NULL UNIQUE)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await gather(self.db.execute('CREATE TABLE IF NOT EXISTS STUDENTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'NAME TEXT NOT NULL,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE,'
                                     'COURSE_WORKS BIGINT[])'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS COURSE_WORKS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'STUDENT BIGINT NOT NULL,'
                                     'SUBJECTS TEXT[] NOT NULL,'
                                     'DESCRIPTION TEXT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ACCEPTED('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'STUDENT BIGINT NOT NULL UNIQUE,'
                                     'SUBJECTS TEXT[] NOT NULL,'
                                     'DESCRIPTION TEXT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUBJECTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'SUBJECT TEXT NOT NULL UNIQUE,'
                                     'COUNT INT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'NAME TEXT NOT NULL,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE,'
                                     'SUBJECTS TEXT[],'
                                     'LOAD INT,'
                                     'STUDENTS BIGINT[])'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ADMINS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE)'))
        await self.db.commit()

    # students
    async def assemble_students_dict(self, cursor):
        list = []
        for i in cursor:
            line = {
                'id': i[0],
                'name': i[1],
                'chat_id': i[2],
                'course_works': await self.get_course_works(student=i[3]),
            }
            list.append(line)
        return list

    async def get_students(self, student=None, chat_id=None):
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        values = []
        if student is not None:
            values = await self.db.execute('SELECT * FROM STUDENTS '
                                           'WHERE ID = %s', (student,))
            return await self.assemble_students_dict(await values.fetchall())
        if chat_id is not None:
            values = await self.db.execute('SELECT * FROM STUDENTS '
                                           'WHERE CHAT_ID = %s', (chat_id,))
            return await self.assemble_students_dict(await values.fetchall())
        return await self.assemble_students_dict(
            await (await self.db.execute('SELECT * FROM STUDENTS')).fetchall()
        )

    # course works
    async def add_subject(self, subject):
        """
        Inserts a string into SUBJECTS table

        Parameters
        ----------
        subject : str
            string of subject

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('INSERT INTO SUBJECTS(SUBJECT, COUNT) '
                              'VALUES(%s, 1) '
                              'ON CONFLICT (SUBJECT) DO '
                              'UPDATE SET COUNT = EXCLUDED.COUNT + 1', (subject,))
        await self.db.commit()

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
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        tasks = []
        work = (await (await self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                                             'DEFAULT, %(chat_id)s, '
                                             '%(subjects)s, %(description)s) '
                                             'RETURNING ID', line)).fetchone())[0]
        tasks.append(self.db.execute('INSERT INTO STUDENTS VALUES('
                                     'DEFAULT, %s, %s, %s) '
                                     'ON CONFLICT (CHAT_ID) DO '
                                     'UPDATE SET COURSE_WORKS = '
                                     'ARRAY_APPEND(EXCLUDED.COURSE_WORKS, '
                                     'CAST(%s as BIGINT))',
                                     (line['name'], line['chat_id'], [work], work,)))
        for subj in line['subjects']:
            tasks.append(self.add_subject(subj))
        await gather(*tasks)
        await self.db.commit()

    async def assemble_courses_dict(self, cursor):
        list = []
        for i in cursor:
            line = {
                'id': i[0],
                'student': i[1],
                'subjects': i[2],
                'description': i[3],
            }
            list.append(line)
        return list

    async def get_course_works(self, subjects=[], student=None):
        """
        Gets all submitted course works that satisfy the argument subject
        Subject may be empty, in this case, return all course works

        Parameters
        ----------
        subjects : list
            List of all strings, indicating needed subjects
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
        if subjects:
            query = 'SELECT * FROM COURSE_WORKS WHERE %s = ANY(SUBJECTS)'
            for subj in range(len(subjects) - 1):
                query += ' AND %s = ANY(SUBJECTS)'
            res = await (await self.db.execute(query,
                                               tuple(subjects))).fetchall()
            return await self.assemble_courses_dict(res)
        if student is not None:
            res = await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                               'WHERE STUDENT = %s',
                                               (student,))).fetchall()
            return await self.assemble_courses_dict(res)
        res = await (await self.db.execute('SELECT * FROM COURSE_WORKS')).fetchall()
        return await self.assemble_courses_dict(res)

    async def get_student_course_works(self, chat_id_):
        """
        Gets all submitted course works from a specified student

        Parameters
        ----------
        chat_id : int
            ID of a specific student

        Raises
        ------
        DBAccessError whatever

        Returns
        ------
        iterable
            Iterable over all compliant lines (dict of columns excluding ID)
        """
        import warnings
        warnings.warn('Don\'t use get_student_course_works, use get_course_works with student argument instead')
        id = await self.get_students(chat_id=chat_id_)
        return await self.get_course_works(id[0]['id'])

    async def modify_course_work(self, line):
        """
        Modifies an existing line in the database, matching 'chat_id' field
        Modifying a course work may update SUBJECTS table if subject is changed

        Parameters
        ----------
        line : dict
            Dict field names are 'student': int, 'subjects': str[], 'desc': str
        Raises
        ------
        DBAccessError whatever
        DBDoesNotExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        old = await (await self.db.execute('SELECT SUBJECTS FROM COURSE_WORKS '
                                           'WHERE STUDENT = %(chat_id)s',
                                           line)).fetchone()[0]
        tasks = []
        for new in list(set(line['subjects']).difference(old)):
            tasks.append(self.add_subject(new))
        for removed in list(set(old).difference(line['subjects'])):
            tasks.append(self.db.execute('UPDATE SUBJECTS '
                                         'SET COUNT = COUNT - 1 '
                                         'WHERE SUBJECT = %s', (removed,)))
        tasks.append(self.db.execute('UPDATE COURSE_WORKS '
                                     'SET SUBJECTS = %(subjects)s, '
                                     'DESCRIPTION = %(description)s '
                                     'WHERE CHAT_ID = %(chat_id)s', line))
        await gather(*tasks)
        await self.db.commit()

    async def remove_course_work(self, id_field):
        """
        Removes a line from COURSE_WORKS table
        Removing a course work decrements COUNT column in SUBJECTS table

        Parameters
        ----------
        id : int
            The first column of the table

        Raises
        ------
        DBAccessError whatever
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('DELETE FROM COURSE_WORKS '
                              'WHERE STUDENT = %s', (id_field,))
        student_relevant = (await (await self.db.execute('SELECT EXISTS('
                                                         'SELECT * FROM COURSE_WORKS '
                                                         'WHERE STUDENT = %s)',
                                                         (id_field,))).fetchone())[0]
        if not student_relevant:
            await self.db.execute('DELETE FROM STUDENTS '
                                  'WHERE CHAT_ID = %s', (id_field,))
        await self.db.commit()

    # accepted
    async def accept_work(self, mentor_id, work_id):
        """
        Moves a line from COURSE_WORKS to ACCEPTED table, increments LOAD
        column in MENTORS table and appends ID into COURSE_WORKS column
        Does nothing if a line exists

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        print(work_id)
        line = await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                            'WHERE ID = %s', (work_id,))).fetchone()
        await self.db.execute('INSERT INTO ACCEPTED VALUES('
                              '%s, %s, %s, %s) '
                              'ON CONFLICT (STUDENT) DO NOTHING',
                              (line[0], line[1], line[2], line[3],))
        #                      id      student  subjects  description
        await self.db.execute('DELETE FROM COURSE_WORKS '
                              'WHERE ID = %s', (work_id,))
        await self.db.execute('UPDATE MENTORS SET LOAD = LOAD + 1, '
                              'STUDENTS = ARRAY_APPEND(STUDENTS, CAST(%S AS BIGINT))'
                              'WHERE ID = %s', (line[1], mentor_id,))
        #                                      student
        await self.db.commit()

    async def readmission_work(self, work):
        """
        Copies a line from ACCEPTED table to COURSE_WORKS table

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        line = await (await self.db.execute('SELECT * FROM ACCEPTED '
                                            'WHERE STUDENT = %(student)s AND '
                                            'DESCRIPTION = %(description)s', work)).fetchone()
        await self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                              '%s, %s, %s, %s)',
                              (line[0], line[1], line[2], line[3],))
        await self.db.commit()

    async def get_accepted(self, subjects=[], student=None):
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if subjects:
            res = await (await self.db.execute('SELECT * FROM ACCEPTED '
                                               'WHERE SUBJECTS = ANY(%s)',
                                               (subjects,))).fetchall()
            return await self.assemble_courses_dict(res)
        if student:
            res = await (await self.db.execute('SELECT * FROM ACCEPTED '
                                               'WHERE STUDENT = %s',
                                               (student,))).fetchall()
            return await self.assemble_courses_dict(res)
        res = await (await self.db.execute('SELECT * FROM ACCEPTED')).fetchall()
        return await self.assemble_courses_dict(res)

    # mentor
    async def add_mentor(self, line):
        """
        Adds a new mentor to the database

        Parameters
        ----------
        line : dict
            Dict field names are corresponding to MENTORS table column
            lowercase names, types are corresponding

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        tasks = []
        tasks.append(self.db.execute('INSERT INTO MENTORS VALUES('
                                     'DEFAULT, %(name)s, %(chat_id)s,'
                                     '%(subjects)s, 0, NULL)', line))
        if line['subjects'] is not None:
            for subj in line['subjects']:
                tasks.append(self.add_subject(subj))
        await gather(*tasks)
        await self.db.commit()

    async def assemble_mentors_dict(self, cursor):
        list = []
        for i in cursor:
            students = []
            if i[5] is not None:
                students = [await self.get_students(student=id)[0] for id in i[5]]
            line = {
                'id': i[0],
                'name': i[1],
                'chat_id': i[2],
                'subjects': i[3],
                'load': i[4],
                'students': students,
            }
            list.append(line)
        return list

    async def get_mentors(self, chat_id=None):
        """
        Gets all lines from MENTORS table

        Returns
        ------
        iterable
            Iterable over all mentors (dict of columns excluding ID)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        mentors = None
        if chat_id is not None:
            mentors = await (await self.db.execute('SELECT * FROM MENTORS '
                                                   'WHERE CHAT_ID = %s',
                                                   (chat_id,))).fetchone()
            if mentors is None:
                return None  # raise
        else:
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

    async def remove_mentor(self, chat_id):
        """
        Removes a line from MENTORS table

        Parameters
        ----------
        chat_id : int
            Chat_id of mentor to delete

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('DELETE FROM MENTORS '
                              'WHERE CHAT_ID = %s', (chat_id,))

    async def add_mentor_subjects(self, id, subject):
        """
        Appends a string into SUBJECTS array of a mentor with a specified ID

        Parameters
        ----------
        id : int
            ID (not chat_id) of mentor to edit
        subjects : str
            string of subject

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('UPDATE MENTORS '
                              'SET SUBJECTS = (CASE WHEN SUBJECTS IS NULL THEN %s '
                              '               ELSE SUBJECTS || %s '
                              '               END) '
                              'WHERE ID = %s', (subject, subject, id,))
        await self.db.commit()

    async def remove_mentor_subject(self, id, subject):
        """
        Removes a string from SUBJECTS array of a mentor with a specified ID

        Parameters
        ----------
        id : int
            ID (not chat_id) of mentor to edit
        subjects : str
            string of subject

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('UPDATE MENTORS '
                              'SET SUBJECTS = ARRAY_REMOVE(SUBJECTS, %s) '
                              'WHERE ID = %s', (subject, id,))
        await self.db.commit()

    # subjects
    async def get_subjects(self):
        """
        Gets all lines from SUBJECTS table

        Returns
        ------
        iterable
            Iterable over all subjects (str's)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        cur = await (await self.db.execute('SELECT * FROM SUBJECTS')).fetchall()
        return [subj[1] for subj in cur]

    # admin
    async def add_admin(self, chat_id):
        """
        Adds a line to ADMINS table

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('INSERT INTO ADMINS VALUES('
                              'DEFAULT, %s,', chat_id)
        await self.db.commit()

    async def get_admins(self):
        """
        Gets all lines from ADMINS table

        Returns
        ------
        iterable
            Iterable over all subjects (str's)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        cur = await (await self.db.execute('SELECT * FROM ADMINS')).fetchall()
        return [adm[1] for adm in cur]

    async def check_is_admin(self, chat_id):
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
                                             'SELECT * FROM ADMINS '
                                             'WHERE CHAT_ID = %s)',
                                             (chat_id,))).fetchone())[0]

    async def remove_admin(self, chat_id):
        """
        Removes a line from ADMINS table

        Parameters
        ----------
        chat_id : int
            The first column of the table

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('DELETE FROM ADMINS '
                              'WHERE CHAT_ID = %s', (chat_id,))
        await self.db.commit()
