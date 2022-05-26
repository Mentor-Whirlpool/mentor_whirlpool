import asynctest
from asyncio import gather
from database import Database
import random
import string


class TestDatabase(asynctest.TestCase):
    async def test_initdb(self):
        self.db = Database()
        await self.db.initdb()
        expected_tables = [('students',)('course_works',), ('accepted',), ('subjects',),
                           ('mentors',), ('admins',)]
        # executemany is screwed
        for table in expected_tables:
            exists = await (await self.db.db.execute("""
            SELECT EXISTS(
            SELECT FROM information_schema.tables
            WHERE table_catalog = \'mentor_whirlpool\' AND
            table_name = %s)
            """, table)).fetchone()
            self.assertEqual((True,), exists)

    async def test_add_subject_controlled(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM SUBJECTS')
        subjects_dup = ['SQL Injection', '\' OR 1=1 OR \'', 'SQL Injection']
        subjects = ['SQL Injection', '\' OR 1=1 OR \'']
        tasks = []
        for subj in subjects_dup:
            tasks.append(self.db.add_subject(subj))
        await gather(*tasks)
        subjects.sort()
        dbsubj = await self.db.get_subjects()
        dbsubj.sort()
        self.assertListEqual(subjects, dbsubj)

    async def test_add_subject_random(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM SUBJECTS')
        # get 1000 random 10 character strings
        subjects = [(''.join(random.choice(string.printable) for i in range(10))) for j in range(1000)]
        tasks = []
        for subj in subjects:
            tasks.append(self.db.add_subject(subj))
        await gather(*tasks)
        # we cannot be sure which order they end up in
        subjects.sort()
        dbsubj = await self.db.get_subjects()
        dbsubj.sort()
        self.assertListEqual(subjects, dbsubj)

    async def test_add_remove_mentor(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM MENTORS')
        subj = ['SQL Injection', 'TestSubj']
        mentors = [{
                'name': name,
                'chat_id': random.randint(0, 99999999),
                'subjects': subj,
            } for name in ['Alice', 'Bob', 'Victor', 'Eugene']]
        mentors.append(
            {
                'name': 'Yoshi',
                'chat_id': random.randint(0, 9999999999),
                'subjects': None
            }
                      )
        tasks = []
        for mentor in mentors:
            tasks.append(self.db.add_mentor(mentor))
        await gather(*tasks)
        mentors.sort(key=lambda x: x['name'])
        dbmentors = await self.db.get_mentors()
        dbmentors.sort(key=lambda x: x['name'])
        self.assertListEqual(mentors, dbmentors)
        mentors.remove(2)
        await self.db.remove_mentor(mentors[2]['chat_id'])
        dbmentors = await self.db.get_mentors()
        dbmentors.sort(key=lambda x: x['name'])
        self.assertListEqual(mentors, dbmentors)

    async def test_add_remove_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM COURSE_WORKS')
        # get 1000 random 10 character strings
        subjects = [(''.join(random.choice(string.printable) for i in range(10))) for j in range(1000)]
        names = [(''.join(random.choice(string.printable) for i in range(10))) for j in range(1000)]
        descriptions = [(''.join(random.choice(string.printable) for i in range(10))) for j in range(1000)]
        course_works = [{
                'name': names[i],
                'chat_id': i,
                'subjects': random.sample(subjects, 10),
                'description': random.choice(descriptions)
            } for i in range(len(names))]
        tasks = []
        for work in course_works:
            tasks.append(self.db.add_course_work(work))
        await gather(*tasks)
        course_works.sort(key=lambda x: x['chat_id'])
        dbworks = await self.db.get_course_works()
        dbworks.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(course_works, dbworks)
        to_remove = list(dict.fromkeys([random.randint(0, len(course_works)) for i in range(20)]))
        # does not affect anything, only needed for source list deletion
        to_remove.sort()
        print(to_remove)
        tasks = []
        for rem in to_remove:
            tasks.append(self.db.remove_course_work(course_works[rem]['chat_id']))
        await gather(*tasks)
        for i in range(len(to_remove)):
            course_works.pop(to_remove[i] - i)
        dbworks = await self.db.get_course_works()
        dbworks.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(course_works, dbworks)


def runtests():
    test_case = TestDatabase("test_initdb")
    test_case.run()
