import psycopg
from asyncio import create_task, gather


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
                Table "COURSE_WORKS":
        ID(PRIMARY KEY) | NAME(TEXT NOT NULL) |
        CHAT_ID(BIGINT / at least 52 bits NOT NULL) |
        SUBJECTS(TEXT[] NOT NULL) | DESCRIPTION(TEXT)
                Table "ACCEPTED":
        ID(PRIMARY KEY) | NAME(TEXT NOT NULL) |
        CHAT_ID(BIGING / at least 52 bits NOT NULL) |
        SUBJECTS(TEXT[] NOT NULL) | DESCRIPTION(TEXT)
                Table "SUBJECTS":
        ID(PRIMARY KEY) | SUBJECT(TEXT NOT NULL) | COUNT(INT)
                Table "MENTORS":
        ID(PRIMARY KEY) | NAME(TEXT NOT NULL) |
        CHAT_ID(BIGINT / at least 52 bits NOT NULL) | SUBJECTS(TEXT[]) |
        LOAD(INT) | COURSE_WORKS (PRIMARY KEY[])
                Table "ADMINS":
        ID(PRIMARY KEY) | CHAT_ID (BIGINT / at least 52 bits NOT NULL)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await gather(self.db.execute('CREATE TABLE IF NOT EXISTS COURSE_WORKS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'NAME TEXT NOT NULL,'
                                     'CHAT_ID BIGINT NOT NULL,'
                                     'SUBJECTS TEXT[] NOT NULL,'
                                     'DESCRIPTION TEXT'
                                     ')'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ACCEPTED('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'NAME TEXT NOT NULL,'
                                     'CHAT_ID BIGINT NOT NULL,'
                                     'SUBJECTS TEXT[] NOT NULL,'
                                     'DESCRIPTION TEXT'
                                     ')'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS SUBJECTS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'SUBJECT TEXT NOT NULL,'
                                     'COUNT INT'
                                     ')'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'NAME TEXT NOT NULL,'
                                     'CHAT_ID BIGINT NOT NULL,'
                                     'SUBJECTS TEXT[],'
                                     'LOAD INT,'
                                     'COURSE_WORKS BIGINT[]'
                                     ')'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS ADMINS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'CHAT_ID BIGINT NOT NULL'
                                     ')'))
        await self.db.commit()

    # course works
    async def add_subject(self, subj):
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        if await (await self.db.execute()('SELECT EXISTS('
                                          'SELECT * FROM SUBJECTS'
                                          'WHERE SUBJECT=%s)', subj)).fetchone()[0]:
            await self.db.execute('INSERT INTO SUBJECTS'
                                  'VALUES(DEFAULT, %s, 1)', subj)
        else:
            await self.db.execute('UPDATE SUBJECTS'
                                  'SET COUNT = COUNT + 1'
                                  'WHERE SUBJECT = %s', subj)

    async def add_course_work(self, line):
        """
        Adds a new course work to the database
        Adding a course work increments COUNT column in SUBJECTS table

        Parameters
        ----------
        line : dict
            Dict field names are corresponding to COURSE_WORKS table column
            lowercase names, types are corresponding

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        tasks = []
        tasks.append(self.db.execute('INSERT INTO COURSE_WORKS VALUES('
                                     'DEFAULT, %(name)s, %(chat_id)s,'
                                     '%(subjects)s, %(description)s)', line))
        for subj in line['subjects']:
            tasks.append(self.add_subject(subj))
        await gather(tasks)
        await self.db.commit()

    async def assemble_courses_dict(cursor):
        list = []
        for i in cursor:
            line = {
                'name': i[1],
                'chat_id': i[2],
                'subjects': i[3],
                'description': i[4]
            }
            list.append(line)
        return list

    async def get_course_works(self, subjects=[]):
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
        if not subjects:
            res = await (await self.db.execute('SELECT * FROM COURSE_WORKS')).fetchall()
            return await self.assemble_courses_dict(res)
        else:
            res = await (await self.db.execute('SELECT * FROM COURSE_WORKS'
                                               'WHERE SUBJECTS = ANY(%s)',
                                               (subjects,))).fetchall()
            return await self.assemble_courses_dict(res)

    async def modify_course_work(self, line):
        """
        Modifies an existing line in the database, matching 'chat_id' field
        Modifying a course work may update SUBJECTS table if subject is changed

        Parameters
        ----------
        line : dict
            Dict field names are corresponding to COURSE_WORKS table column
            lowercase names, types are corresponding
        Raises
        ------
        DBAccessError whatever
        DBDoesNotExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        old = await (await self.db.execute('SELECT SUBJECTS FROM COURSE_WORKS'
                                           'WHERE CHAT_ID = %s',
                                           line['chat_id'])).fetchone()[0]
        tasks = []
        for new in list(set(line['subjects']).difference(old)):
            tasks.append(self.add_subject(new))
        for removed in list(set(old).difference(line['subjects'])):
            tasks.append(self.db.execute('UPDATE SUBJECTS'
                                         'SET COUNT = COUNT - 1'
                                         'WHERE SUBJECT = %s', removed))
        tasks.append(self.db.execute('UPDATE COURSE_WORKS'
                                     'SET SUBJECTS = %(subjects)s,'
                                     'DESCRIPTION = %(description)s'
                                     'WHERE CHAT_ID = %(chat_id)s', line))
        await gather(tasks)
        await self.db.commit()

    async def remove_course_work(self, id):
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
        await self.db.execute('DELETE FROM COURSE_WORKS'
                              'WHERE CHAT_ID = %s', (id,))

    # accepted
    async def accept_work(self, mentor, work):
        """
        Moves a line from COURSE_WORKS to ACCEPTED table, increments LOAD
        column in MENTORS table and appends ID into COURSE_WORKS column

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        DBAlreadyExists
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        line = await (await self.db.execute('SELECT * FROM COURSE_WORKS'
                                            'WHERE NAME = %(name)s AND '
                                            'CHAT_ID = %(chat_id)s AND '
                                            'DESCRIPTION = %(chat_id)s')).fetchone()
        await self.db.execute('INSERT INTO ACCEPTED VALUES('
                              'DEFAULT, %s, %s, %s, %s)', line[1:]) # probably bad (not comma ended)
        await self.db.execute('DELETE FROM COURSE_WORKS'
                              'WHERE NAME = %(name)s AND '
                              'CHAT_ID = %(chat_id)s AND '
                              'DESCRIPTION = %(chat_id)s')
        await self.db.commit()

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
        await gather(tasks)
        await self.db.commit()

    async def assemble_mentors_dict(self, cursor):
        list = []
        for i in cursor:
            line = {
                'name': i[1],
                'chat_id': i[2],
                'subjects': i[3],
                'load': i[4],
                'course_works': i[5]
            }
            list.append(line)
        return list

    async def get_mentors(self):
        """
        Gets all lines from MENTORS table

        Returns
        ------
        iterable
            Iterable over all mentors (dict of columns excluding ID)
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        mentors = await (await self.db.execute('SELECT * FROM MENTORS')).fetchall()
        return await self.assemble_mentors_dict(mentors)

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
        await self.db.execute('DELETE FROM MENTORS'
                              'WHERE CHAT_ID = %s', (chat_id,))

    # subjects
    async def get_subjects(self):
        """
        Gets all lines from SUBJECTS table

        Returns
        ------
        iterable
            Iterable over all subjects (str's)
        """
        raise NotImplementedError

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
        return *[adm[1] for adm in cur]

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
        await self.db.execute('DELETE FROM ADMINS'
                              'WHERE CHAT_ID = %s', (chat_id,))
        await self.db.commit()
