import psycopg


class AdminsTables:
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
