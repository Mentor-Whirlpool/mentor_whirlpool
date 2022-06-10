import psycopg


class SupportsTables:
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
            if i is None:
                continue
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
<<<<<<< HEAD
            if i is None:
                continue
=======
>>>>>>> 7a8668a (1. Added async actions to asyncio.gather();)
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

    async def check_is_support(self, chat_id):
        """
        Checks if specified chat_id is present in database as a support

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
                                             'SELECT * FROM SUPPORTS '
                                             'WHERE CHAT_ID = %s)',
                                             (chat_id,))).fetchone())[0]
