import psycopg
from os import environ as env
from asyncio import gather
from mentor_whirlpool.database.students_tables import StudentTables
from mentor_whirlpool.database.course_works_tables import CourseWorksTables
from mentor_whirlpool.database.accepted_tables import AcceptedTables
from mentor_whirlpool.database.mentors_tables import MentorsTables
from mentor_whirlpool.database.admins_tables import AdminsTables
from mentor_whirlpool.database.supports_tables import SupportsTables
from mentor_whirlpool.database.subjects_tables import SubjectsTables
from mentor_whirlpool.database.ideas_tables import IdeasTables


class Database(StudentTables, CourseWorksTables, AcceptedTables, MentorsTables,
               IdeasTables, AdminsTables, SupportsTables, SubjectsTables):
    def __init__(self):
        self.db = None
        self.conn_opts = ('dbname=mentor_whirlpool '
                          f'user={env["POSTGRE_USER"]} '
                          f'host={env["POSTGRE_ADDRESS"]} '
                          f'port={env["POSTGRE_PORT"]} '
                          f'password={env["POSTGRE_PASSWD"]}')

    async def initdb(self):
        """
        Creates database model if not declared already
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
                                     'COUNT INT,'
                                     'ARCHIVED BOOLEAN)'),
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
                                     'LOAD INT,'
                                     'ARCHIVED BOOLEAN)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS_SUBJECTS('
                                     'MENTOR BIGINT NOT NULL REFERENCES MENTORS(ID),'
                                     'SUBJECT BIGINT NOT NULL REFERENCES SUBJECTS(ID),'
                                     'UNIQUE(MENTOR, SUBJECT))'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS MENTORS_STUDENTS('
                                     'MENTOR BIGINT NOT NULL REFERENCES MENTORS(ID),'
                                     'STUDENT BIGINT NOT NULL REFERENCES STUDENTS(ID),'
                                     'UNIQUE(MENTOR, STUDENT))'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS IDEAS('
                                     'ID BIGSERIAL PRIMARY KEY,'
                                     'MENTOR BIGINT NOT NULL REFERENCES MENTORS(ID),'
                                     'DESCRIPTION TEXT)'),
                     self.db.execute('CREATE TABLE IF NOT EXISTS IDEAS_SUBJECTS('
                                     'IDEA BIGINT NOT NULL REFERENCES IDEAS(ID),'
                                     'SUBJECT BIGINT NOT NULL REFERENCES SUBJECTS(ID),'
                                     'UNIQUE(IDEA, SUBJECT))'),
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
