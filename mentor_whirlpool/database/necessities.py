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
                                     'CHAT_ID BIGINT NOT NULL UNIQUE)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS COURSE_WORKS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'STUDENT BIGINT NOT NULL REFERENCES STUDENTS(ID),'
                                     'DESCRIPTION TEXT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUBJECTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'SUBJECT TEXT NOT NULL UNIQUE,'
                                     'COUNT INT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS COURSE_WORKS_SUBJECTS('
                                     'COURSE_WORK BIGINT NOT NULL REFERENCES COURSE_WORKS(ID),'
                                     'SUBJECT BIGINT NOT NULL REFERENCES SUBJECTS(ID),'
                                     'UNIQUE(COURSE_WORK, SUBJECT))'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ACCEPTED('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'STUDENT BIGINT NOT NULL UNIQUE REFERENCES STUDENTS(ID),'
                                     'DESCRIPTION TEXT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ACCEPTED_SUBJECTS('
                                     'COURSE_WORK BIGINT NOT NULL REFERENCES ACCEPTED(ID),'
                                     'SUBJECT BIGINT NOT NULL REFERENCES SUBJECTS(ID),'
                                     'UNIQUE(COURSE_WORK, SUBJECT))'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'NAME TEXT NOT NULL,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE,'
                                     'LOAD INT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS_SUBJECTS('
                                     'MENTOR BIGINT NOT NULL REFERENCES MENTORS(ID),'
                                     'SUBJECT BIGINT NOT NULL REFERENCES SUBJECTS(ID),'
                                     'UNIQUE(MENTOR, SUBJECT))'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS_STUDENTS('
                                     'MENTOR BIGINT NOT NULL REFERENCES MENTORS(ID),'
                                     'STUDENT BIGINT NOT NULL REFERENCES STUDENTS(ID),'
                                     'UNIQUE(MENTOR, STUDENT))'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ADMINS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUPPORTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE,'
                                     'NAME TEXT NOT NULL)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUPPORT_REQUESTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL UNIQUE,'
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

        Returns
        -------
        int
            Database ID of inserted subject
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await self.db.execute('INSERT INTO SUBJECTS VALUES(DEFAULT, %s, 1) '
                              'ON CONFLICT (SUBJECT) DO '
                              'UPDATE SET COUNT = EXCLUDED.COUNT + 1 ',
                              (subject,))
        (id_f,) = await (await self.db.execute('SELECT ID FROM SUBJECTS '
                                               'WHERE SUBJECT = %s', (subject,))).fetchone()
        await self.db.commit()
        return id_f

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
        subj_ids = await gather(*[self.add_subject(subj) for subj in line['subjects']])
        await gather(*[self.db.execute('INSERT INTO COURSE_WORKS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING', (work, subj,))
                       for subj in subj_ids])
        await self.db.commit()
        return work

    async def assemble_courses_dict(self, cursor):
        list = []
        for i in cursor:
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
        subjects : iterable(str)
            All strings, indicating needed subjects
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
            subj_ids = [cur for (cur,) in
                        [await (await self.db.execute('SELECT ID FROM SUBJECTS '
                                                      'WHERE SUBJECT = %s', (subj,))).fetchone()
                         for subj in subjects]]
            ids = await (await self.db.execute('SELECT COURSE_WORK FROM COURSE_WORKS_SUBJECTS '
                                               'WHERE SUBJECT = ANY(%s)', (subj_ids,))).fetchall()
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

    async def get_student_course_works(self, chat_id_):  # pragma: no cover
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
        return await self.get_course_works(id[0]['course_works'][0]['subjects'])

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
        cw_subj = await (await self.db.execute('SELECT SUBJECT FROM COURSE_WORKS_SUBJECTS '
                                               'WHERE COURSE_WORK = %s', (work_id,))).fetchall()
        if line is None:
            return
        await gather(self.db.execute('INSERT INTO ACCEPTED VALUES('
                                     '%s, %s, %s) '
                                     'ON CONFLICT (STUDENT) DO NOTHING',
                                     (line[0], line[1], line[2],)),
                                     # id      student  description
                     *[self.db.execute('INSERT INTO ACCEPTED_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING',
                                       (work_id, subj))
                       for (subj,) in cw_subj],
                     self.remove_course_work(line[0]),
                     self.db.execute('UPDATE MENTORS SET LOAD = LOAD + 1 '
                                     'WHERE ID = %s', (mentor_id,)),
                     self.db.execute('INSERT INTO MENTORS_STUDENTS VALUES('
                                     '%s, %s)', (mentor_id, line[1],)))
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
        cw_subj = await (await self.db.execute('SELECT SUBJECT FROM ACCEPTED_SUBJECTS '
                                               'WHERE COURSE_WORK = %s', (work_id,))).fetchall() 
        if line is None:
            return
        await gather(self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                                     '%s, %s, %s)',
                                     (line[0], line[1], line[2],)),
                     #                id      student  description
                     *[self.db.execute('INSERT INTO COURSE_WORKS_SUBJECTS VALUES('
                                       '%s, %s) ON CONFLICT DO NOTHING',
                                       (work_id, subj))
                       for (subj,) in cw_subj],
                     self.db.execute('DELETE FROM ACCEPTED_SUBJECTS '
                                     'WHERE COURSE_WORK = %s', (work_id,)),
                     self.db.execute('DELETE FROM ACCEPTED '
                                     'WHERE ID = %s', (work_id,)),
                     self.db.execute('UPDATE MENTORS SET LOAD = LOAD + 1 '
                                     'WHERE ID = %s', (mentor_id,)),
                     self.db.execute('DELETE FROM MENTORS_STUDENTS '
                                     'WHERE MENTOR = %s AND '
                                     'STUDENT = %s', (mentor_id, line[1],)))
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
                              '%s, %s, %s)',
                              (line[0], line[1], line[2],))
        await self.db.commit()

    async def get_accepted(self, id_field=None, subjects=[], student=None):
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if id_field is not None:
            res = [await (await self.db.execute('SELECT * FROM ACCEPTED'
                                                'WHERE ID = %s', (id_field,))).fetchone()]
            return await self.assemble_courses_dict(res)
        if subjects:
            ids = [cur for (cur,) in
                   await (await self.db.execute('SELECT COURSE_WORK FROM COURSE_WORKS_SUBJECTS '
                                                'WHERE SUBJECT = ANY(%s)', tuple(subjects))).fetchall()]
            works = [await (await self.db.execute('SELECT * FROM ACCEPTED '
                                                  'WHERE ID = %s', (id_f,))).fetchone()
                     for id_f in ids]
            return await self.assemble_courses_dict(works)
        if student is not None:
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
        await gather(self.db.execute('DELETE FROM MENTORS_SUBJECTS '
                                     'WHERE MENTOR = %s', (id_field,)),
                     self.db.execute('DELETE FROM MENTORS_STUDENTS '
                                     'WHERE MENTOR = %s', (id_field,)),
                     self.db.execute('DELETE FROM MENTORS '
                                     'WHERE ID = %s', (id_field,)))

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

    # subjects
    async def get_subjects(self, id_field=None, work_id=None, mentor_id=None):
        """
        Gets all lines from SUBJECTS table

        Parameters
        ---------
        id_field : int or None
            Database ID of subject
        work_id : int or None
            Database ID of course work to get subjects from
        mentor_id : int or None
            Database ID of mentor to get subjects from

        Returns
        ------
        iterable
            Iterable over all subjects (str's)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if work_id is not None:
            # this code right here may look horrible and ugly and unreadable
            # and that may be true, but doing it this way, according to the
            # testsm is cutting overall time in this function threefold,
            # leaving most of the time spent asynchronously waiting for
            # database to respond. this branch can only be improved with
            # less lists comprehension, but even then that's debatable
            ids = await (await self.db.execute('SELECT SUBJECT FROM COURSE_WORKS_SUBJECTS '
                                               'WHERE COURSE_WORK = %s',
                                               (work_id,))).fetchall()
            subj_cur = await gather(*[self.db.execute('SELECT SUBJECT FROM SUBJECTS '
                                                      'WHERE ID = %s', (id_f,))
                                      for (id_f,) in ids])
            subjects = await gather(*[subj.fetchone()
                                      for subj in subj_cur])
            ids = await (await self.db.execute('SELECT SUBJECT FROM ACCEPTED_SUBJECTS '
                                               'WHERE COURSE_WORK = %s', (work_id,))).fetchall()
            subj_cur = await gather(*[self.db.execute('SELECT SUBJECT FROM SUBJECTS '
                                                      'WHERE ID = %s', (id_f,))
                                      for (id_f,) in ids])
            subjects += await gather(*[subj.fetchone()
                                      for subj in subj_cur])
            return [subj[0] for subj in subjects]
        if mentor_id is not None:
            ids = [cur for (cur,) in
                   await (await self.db.execute('SELECT SUBJECT FROM MENTORS_SUBJECTS '
                                                'WHERE MENTOR = %s',
                                                (mentor_id,))).fetchall()]
            ids = set(ids)
            subjects = [(await (await self.db.execute('SELECT SUBJECT FROM SUBJECTS '
                                                      'WHERE ID = %s', (id_f,))).fetchone())[0]
                        for id_f in ids]
            return subjects

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
                              'DEFAULT, %(chat_id)s, %(name)s, %(issue)s, NULL)'
                              'ON CONFLICT DO NOTHING',
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
