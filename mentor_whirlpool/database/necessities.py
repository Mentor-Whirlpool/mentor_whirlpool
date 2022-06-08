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
                Table "SUPPORTS":
        ID(PRIMARY KEY) | CHAT_ID (BIGINT NOT NULL UNIQUE) |
        REQUESTS(BIGINT[] REFERENCES SUPPORT_REQUESTS(ID))
                Table "SUPPORT_REQUESTS":
        ID(PRIMARY KEY) | REQUESTER (BIGINT NOT NULL)
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
                                     'CHAT_ID BIGINT NOT NULL UNIQUE)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUPPORTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE,'
                                     'NAME TEXT NOT NULL)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUPPORT_REQUESTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL,'
                                     'NAME TEXT NOT NULL,'
                                     'ISSUE TEXT,'
                                     'SUPPORT BIGINT REFERENCES SUPPORTS(ID) DEFERRABLE INITIALLY DEFERRED)'))
        await self.db.commit()

    # students
    async def assemble_students_dict(self, cursor):
        list = []
        for i in cursor:
            line = {
                'id': i[0],
                'name': i[1],
                'chat_id': i[2],
                'course_works': (await self.get_course_works(student=i[0]) +
                                 await self.get_accepted(student=i[0])),
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
        await self.db.execute('INSERT INTO STUDENTS VALUES('
                              'DEFAULT, %s, %s, %s) '
                              'ON CONFLICT (CHAT_ID) DO NOTHING ',
                              # 'UPDATE SET COURSE_WORKS = '
                              # 'ARRAY_APPEND(EXCLUDED.COURSE_WORKS, '
                              # 'CAST(%s as BIGINT))',
                              # (line['name'], line['chat_id'], [work], work,)))
                              (line['name'], line['chat_id'], [],))
        stud_id = (await self.get_students(chat_id=line['chat_id']))[0]['id']
        work = (await (await self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                                             'DEFAULT, %s, %s, %s) '
                                             'RETURNING ID',
                                             (stud_id, line['subjects'],
                                              line['description'],))).fetchone())[0]
        await self.db.execute('UPDATE STUDENTS SET COURSE_WORKS = '
                              'ARRAY_APPEND(COURSE_WORKS, CAST(%s as BIGINT)) '
                              'WHERE ID = %s', (work, stud_id,))
        tasks = []
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

    async def get_course_works(self, id=None, subjects=[], student=None):
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
        if id is not None:
            res = [await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                                'WHERE ID = %s', (id,))).fetchone()]
            return await self.assemble_courses_dict(res)
        if subjects:
            query = 'SELECT * FROM COURSE_WORKS WHERE %s = ANY(SUBJECTS)'
            for subj in range(len(subjects) - 1):
                query += ' OR %s = ANY(SUBJECTS)'
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

    async def get_student_course_works(self, chat_id_): # pragma: no cover
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
            Dict field names are 'id': int, 'subjects': str[], 'description': str

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        (old,) = await (await self.db.execute('SELECT SUBJECTS FROM COURSE_WORKS '
                                              'WHERE ID = %(id)s',
                                              line)).fetchone()
        tasks = []
        for new in set(line['subjects']).difference(old):
            tasks.append(self.add_subject(new))
        for removed in set(old).difference(line['subjects']):
            tasks.append(self.db.execute('UPDATE SUBJECTS '
                                         'SET COUNT = COUNT - 1 '
                                         'WHERE SUBJECT = %s', (removed,)))
        tasks.append(self.db.execute('UPDATE COURSE_WORKS '
                                     'SET SUBJECTS = %(subjects)s, '
                                     'DESCRIPTION = %(description)s '
                                     'WHERE ID = %(id)s', line))
        await gather(*tasks)
        await self.db.commit()

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
        await self.db.execute('DELETE FROM COURSE_WORKS '
                              'WHERE STUDENT = %s', (id_field,))
        await self.db.execute('DELETE FROM STUDENTS '
                              'WHERE ID = %s', (id_field,))
        await self.db.commit()

    async def remove_course_work(self, id_field):
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
        await self.db.execute('DELETE FROM COURSE_WORKS '
                              'WHERE ID = %s', (id_field,))
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

        Parameters
        ----------
        mentor_id : int
            database id of the mentor
        work_id : int
            database id of the course work

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        line = await (await self.db.execute('SELECT * FROM COURSE_WORKS '
                                            'WHERE ID = %s', (work_id,))).fetchone()
        if line is None:
            return
        await self.db.execute('INSERT INTO ACCEPTED VALUES('
                              '%s, %s, %s, %s) '
                              'ON CONFLICT (STUDENT) DO NOTHING',
                              (line[0], line[1], line[2], line[3],))
        #                      id      student  subjects  description
        await self.db.execute('DELETE FROM COURSE_WORKS '
                              'WHERE ID = %s', (work_id,))
        await self.db.execute('UPDATE MENTORS SET LOAD = LOAD + 1, '
                              'STUDENTS = ARRAY_APPEND(STUDENTS, CAST(%s AS BIGINT))'
                              'WHERE ID = %s', (line[1], mentor_id,))
        #                                      student
        await self.db.commit()

    async def reject_work(self, mentor_id, work_id):
        """
        Disown a student

        Moves a line from ACCEPTED to COURSE_WORK table, decrements LOAD
        column in MENTORS table and subtracts ID from COURSE_WORKS column
        Does nothing if a line does not exist

        Parameters
        ----------
        mentor_id : int
            database id of the mentor
        work_id : int
            database id of the course work

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        line = await (await self.db.execute('SELECT * FROM ACCEPTED '
                                            'WHERE ID = %s', (work_id,))).fetchone()
        if line is None:
            return
        await self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                              '%s, %s, %s, %s)',
                              (line[0], line[1], line[2], line[3],))
        #                      id      student  subjects  description
        await self.db.execute('DELETE FROM ACCEPTED '
                              'WHERE ID = %s', (work_id,))
        await self.db.execute('UPDATE MENTORS SET LOAD = LOAD + 1, '
                              'STUDENTS = ARRAY_REMOVE(STUDENTS, CAST(%s AS BIGINT))'
                              'WHERE ID = %s', (line[1], mentor_id,))
        #                                      student
        await self.db.commit()

    async def readmission_work(self, work_id):
        """
        Copies a line from ACCEPTED table to COURSE_WORKS table

        Parameters
        ----------
        work_id : int
            database id of the course work

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        line = await (await self.db.execute('SELECT * FROM ACCEPTED '
                                            'WHERE ID = %s', (work_id,))).fetchone()
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
            dict with fields 'name', 'chat_id', 'subjects'

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
                students = [(await self.get_students(student=id))[0] for id in i[5]]
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

    async def get_mentors(self, id=None, chat_id=None):
        """
        Gets all lines from MENTORS table

        Parameters
        ----------
        id : int
            database id of the mentor
        chat_id : int
            telegram chat_id of required mentor

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
            if mentors is None:
                return None  # raise
        if chat_id is not None:
            mentors = [await (await self.db.execute('SELECT * FROM MENTORS '
                                                    'WHERE CHAT_ID = %s',
                                                    (chat_id,))).fetchone()]
            if mentors is None:
                return None  # raise
        if id is None and chat_id is None:
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

    async def remove_mentor(self, id=None, chat_id=None):
        """
        Removes a line from MENTORS table

        Parameters
        ----------
        id : int
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
            await self.db.execute('DELETE FROM MENTORS '
                                  'WHERE CHAT_ID = %s', (chat_id,))
        if id is not None:
            await self.db.execute('DELETE FROM MENTORS '
                                  'WHERE ID = %s', (id,))

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
                              'DEFAULT, %s)', (chat_id,))
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
        return [{'id': adm[0], 'chat_id': adm[1]} for adm in cur]

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

    async def remove_admin(self, id=None, chat_id=None):
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
        if id is not None:
            await self.db.execute('DELETE FROM ADMINS '
                                  'WHERE ID = %s', (id,))
        if chat_id is not None:
            await self.db.execute('DELETE FROM ADMINS '
                                  'WHERE CHAT_ID = %s', (chat_id,))
        await self.db.commit()

    # supports
    async def add_support(self, line):
        """
        Adds a support to the database

        Parameters
        ----------
        line : dict
            A dictionary with keys 'chat_id' and 'name'

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('INSERT INTO SUPPORTS VALUES('
                              'DEFAULT, %(chat_id)s, %(name)s)'
                              'ON CONFLICT DO NOTHING', line)
        await self.db.commit()

    async def remove_support(self, id_field=None, chat_id=None):
        """
        Removes a support from the database

        Parameters
        ----------
        id_field : (optional) int
            Database id of the support
        chat_id : (optional) int
            Chat ID of the support
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if id_field is not None:
            await self.db.execute('DELETE FROM SUPPORTS '
                                  'WHERE ID = %s', (id_field,))
        if chat_id is not None:
            await self.db.execute('DELETE FROM SUPPORTS '
                                  'WHERE CHAT_ID = %s', (chat_id,))
        await self.db.commit()

    async def assemble_supports_dict(self, res):
        list = []
        for i in res:
            line = {
                'id': i[0],
                'chat_id': i[1],
                'name': i[2],
            }
            list.append(line)
        return list

    async def get_supports(self, id_field=None, chat_id=None):
        """
        If any arguments are supplied, they are used as a key to find
        a specific support. Otherwise, fetches all supports from the database

        Parameters
        ----------
        id_field : (optional) int
            Database id of the support
        chat_id : (optional) int
            Chat ID of the support

        Returns
        -------
        list(dict)
            A list of dictionaries with keys: 'id' : int, 'chat_id' : int,
            'name' : str
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        res = None
        if id_field is not None:
            res = [await (await self.db.execute('SELECT * FROM SUPPORTS '
                                                'WHERE ID = %s',
                                                (id_field,))).fetchone()]
        if chat_id is not None:
            res = [await (await self.db.execute('SELECT * FROM SUPPORTS '
                                                'WHERE CHAT_ID = %s',
                                                (chat_id,))).fetchone()]
        if res is None:
            res = await (await self.db.execute('SELECT * FROM SUPPORTS')).fetchall()
        return await self.assemble_supports_dict(res)

    async def add_support_request(self, line):
        """
        Adds a support request to the database

        Parameters
        ----------
        line : dict
            Dictionary with keys: 'chat_id' : int, 'name' : str and
            'issue' : str or None
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('INSERT INTO SUPPORT_REQUESTS VALUES('
                              'DEFAULT, %(chat_id)s, %(name)s, %(issue)s, NULL)',
                              line)
        await self.db.commit()

    async def remove_support_request(self, id_field=None):
        """
        Removes a support request from the database

        Parameters
        ----------
        id_field : int
            Database id of the support request
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('DELETE FROM SUPPORT_REQUESTS '
                              'WHERE ID = %s', (id_field,))
        await self.db.commit()

    async def assemble_support_requests_dict(self, cursor):
        list = []
        for i in cursor:
            support = None
            if i[4] is not None:
                support = await self.get_supports(i[4])
            line = {
                'id': i[0],
                'chat_id': i[1],
                'name': i[2],
                'issue': i[3],
                'support': support,
            }
            list.append(line)
        return list

    async def get_support_requests(self, id_field=None, chat_id=None):
        """
        If any arguments are supplied, they are used as a key to find
        a specific support request. Otherwise, fetches all supports requests
        from the database

        Parameters
        ----------
        id_field : (optional) int
            Database id of the support request
        chat_id : (optional) int
            Chat ID of the requester

        Returns
        -------
        list(dict)
            A list of dictionaries with keys: 'id' : int, 'chat_id' : int,
            'name' : str, 'issue' : str or None, 'support' : dict
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        res = None
        if id_field is not None:
            res = [await (await self.db.execute('SELECT * FROM SUPPORT_REQUESTS '
                                                'WHERE ID = %s',
                                                (id_field,))).fetchone()]
        if chat_id is not None:
            res = [await (await self.db.execute('SELECT * FROM SUPPORT_REQUESTS '
                                                'WHERE CHAT_ID = %s',
                                                (chat_id,))).fetchone()]
        if res is None:
            res = await (await self.db.execute('SELECT * FROM SUPPORT_REQUESTS')).fetchall()
        return await self.assemble_support_requests_dict(res)
