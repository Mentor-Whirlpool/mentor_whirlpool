import psycopg
from asyncio import gather

class SubjectsTables:
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

    async def remove_subject(self, subj_id):
        """
        Removes a line from SUBJECTS table and wherever it is situated

        Parameters
        ----------
        subj_id : integer
            Database ID of subject

        Raises
        ------
        DBAccessError whatever
        DBDoesNotExist
        """
        if self.db is None:
            self.db = await psycopg.AsyncConnection.connect(self.conn_opts)
        await gather(self.db.execute('DELETE FROM COURSE_WORKS_SUBJECTS '
                                     'WHERE SUBJECT = %s', (subj_id,)),
                     self.db.execute('DELETE FROM ACCEPTED_SUBJECTS '
                                     'WHERE SUBJECT = %s', (subj_id,)),
                     self.db.execute('DELETE FROM MENTORS_SUBJECTS '
                                     'WHERE SUBJECT = %s', (subj_id,)),
                     self.db.execute('DELETE FROM SUBJECTS '
                                     'WHERE ID = %s', (subj_id,)))
        await self.db.commit()

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
        if id_field is not None:
            subject = await (await self.db.execute('SELECT * FROM SUBJECTS '
                                                   'WHERE ID = %s', (id_field,))).fetchone()
            return [{'id': subject[0], 'subject': subject[1]}]
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
            subj_cur = await gather(*[self.db.execute('SELECT * FROM SUBJECTS '
                                                      'WHERE ID = %s', (id_f,))
                                      for (id_f,) in ids])
            subjects = await gather(*[subj.fetchone()
                                      for subj in subj_cur])
            ids = await (await self.db.execute('SELECT SUBJECT FROM ACCEPTED_SUBJECTS '
                                               'WHERE COURSE_WORK = %s', (work_id,))).fetchall()
            subj_cur = await gather(*[self.db.execute('SELECT * FROM SUBJECTS '
                                                      'WHERE ID = %s', (id_f,))
                                      for (id_f,) in ids])
            subjects += await gather(*[subj.fetchone()
                                      for subj in subj_cur])
            return [{'id': subj[0], 'subject': subj[1]} for subj in subjects]
        if mentor_id is not None:
            ids = [cur for (cur,) in
                   await (await self.db.execute('SELECT SUBJECT FROM MENTORS_SUBJECTS '
                                                'WHERE MENTOR = %s',
                                                (mentor_id,))).fetchall()]
            ids = set(ids)
            subjects = [(await (await self.db.execute('SELECT * FROM SUBJECTS '
                                                      'WHERE ID = %s', (id_f,))).fetchone())
                        for id_f in ids]
            return [{'id': subj[0], 'subject': subj[1]} for subj in subjects]

        cur = await (await self.db.execute('SELECT * FROM SUBJECTS')).fetchall()
        return [{'id': subj[0], 'subject': subj[1]} for subj in cur]
