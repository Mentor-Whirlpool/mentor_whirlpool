class Database:
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
        SUBJECT(TEXT NOT NULL) | DESCRIPTION(TEXT)
                Table "SUBJECTS":
        ID(PRIMARY KEY) | SUBJECT(TEXT NOT NULL) | COUNT(INT)
                Table "MENTORS":
        ID(PRIMARY KEY) | NAME(TEXT NOT NULL) |
        CHAT_ID(BIGINT / at least 52 bits NOT NULL) | LOAD(INT)
                Table "ADMINS":
        ID(PRIMARY KEY) | CHAT_ID (BIGINT / at least 52 bits NOT NULL)
        """
        raise NotImplementedError()

    async def add_course_work(self, line):
        """
        Adds a new course work to the database
        Adding a course work updates SUBJECTS table if needed subject is new

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
        raise NotImplementedError()

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
        raise NotImplementedError()

    async def remove_course_work(self, id):
        """
        Removes a line from COURSE_WORKS table
        Removing a course work may update SUBJECTS table if no other course
        works with the same subject exist

        Parameters
        ----------
        id : int
            The first column of the table

        Raises
        ------
        DBAccessError whatever
        """
        raise NotImplementedError()

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
        raise NotImplementedError

    async def remove_mentor(self, id):
        """
        Removes a line from MENTORS table

        Parameters
        ----------
        id : int
            The first column of the table

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        raise NotImplementedError

    async def get_course_works(self, subject):
        """
        Gets all submitted course works that satisfy the argument subject
        Subject may be empty, in this case, return all course works

        Parameters
        ----------
        subject : list
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
        raise NotImplementedError

    async def get_subjects(self):
        """
        Gets all lines from SUBJECTS table

        Returns
        ------
        iterable
            Iterable over all subjects (str's)
        """
        raise NotImplementedError

    async def get_mentors(self):
        """
        Gets all lines from MENTORS table

        Returns
        ------
        iterable
            Iterable over all mentors (dict of columns excluding ID)
        """
        raise NotImplementedError


    async def add_admin(self, chat_id):
        """
        Adds a line to ADMINS table

        Raises
        ------
        DBAccessError whatever
        DBAlreadyExists
        """
        raise NotImplementedError

