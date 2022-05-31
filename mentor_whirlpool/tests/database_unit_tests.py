import asynctest
from asyncio import gather, sleep
from database import Database
import random
import string


# fine to test altogether, because different tables are tested
class TestDatabaseSimple(asynctest.TestCase):
    async def test_initdb(self):
        self.db = Database()
        await self.db.initdb()
        expected_tables = [('students',), ('course_works',), ('accepted',), ('subjects',),
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
            'chat_id': random.randint(0, 9999),
            'subjects': subj,
        } for name in ['Alice', 'Bob', 'Victor', 'Eugene']]
        mentors.append(
            {
                'name': 'Yoshi',
                'chat_id': random.randint(0, 9999),
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

    def check_contains_student(self, student, dbstudents):
        for stud in dbstudents:
            if stud['name'] == student:
                return True
        return False

    async def test_add_remove_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM COURSE_WORKS')
        await self.db.db.execute('DELETE FROM STUDENTS')
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
        for work in course_works:
            work.pop('name')
            work['student'] = work.pop('chat_id')
        course_works.sort(key=lambda x: x['student'])
        dbworks = await self.db.get_course_works()
        for work in dbworks:
            work.pop('id')
        dbworks.sort(key=lambda x: x['student'])
        self.assertListEqual(course_works, dbworks)
        dbstudents = await self.db.get_students()
        for stud in names:
            self.assertTrue(self.check_contains_student(stud, dbstudents))
        to_remove = list(dict.fromkeys([random.randint(0, len(course_works)) for i in range(20)]))
        # does not affect anything, only needed for source list deletion
        to_remove.sort()
        tasks = []
        for rem in to_remove:
            tasks.append(self.db.remove_course_work(course_works[rem]['student']))
        await gather(*tasks)
        for i in range(len(to_remove)):
            course_works.pop(to_remove[i] - i)
        dbworks = await self.db.get_course_works()
        dbworks.sort(key=lambda x: x['student'])
        for work in dbworks:
            work.pop('id')
        self.assertListEqual(course_works, dbworks)


class TestDatabaseAccepted(asynctest.TestCase):
    async def test_accept_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM COURSE_WORKS')
        await self.db.db.execute('DELETE FROM STUDENTS')
        await self.db.db.execute('DELETE FROM MENTORS')
        await self.db.db.execute('DELETE FROM ACCEPTED')
        course_works = [{
            'name': 'Helen',
            'chat_id': 10000,
            'subjects': ['SQL', 'Qt'],
            'description': None,
        },
            {
                'name': 'Alice',
                'chat_id': 10001,
                'subjects': ['SQL', 'TCP'],
                'description': 'Something',
            },
            {
                'name': 'Bob',
                'chat_id': 10002,
                'subjects': ['TypeScript', 'Crypto'],
                'description': 'Nothing',
            }]
        tasks = []
        for work in course_works:
            tasks.append(self.db.add_course_work(work))
        await gather(*tasks)
        for work in course_works:
            work.pop('name')
            work['student'] = work.pop('chat_id')
        accepted = await self.db.get_accepted()
        self.assertListEqual(accepted, [])
        dbwork = await self.db.get_course_works()
        self.db.add_mentor({
            'name': 'Yoshi',
            'chat_id': 10003,
            'subjects': None
        })
        await self.db.accept_work(4, dbwork[0]['id'])
        accepted = await self.db.get_accepted()
        self.assertListEqual(accepted, [dbwork[0]])


class TestDatabaseFiltered(asynctest.TestCase):
    async def test_filter_for_get_course_works(self):
        self.db = Database()
        await self.db.initdb()
        await self.db.db.execute('DELETE FROM COURSE_WORKS')
        await self.db.db.execute('DELETE FROM STUDENTS')
        # get 1000 random 10 character strings
        subjects = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        names = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        descriptions = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        course_works = [{
            'name': names[i],
            'chat_id': i,
            'subjects': random.sample(subjects, 10),
            'description': random.choice(descriptions)
        } for i in range(len(names))]

        filter_subjects = random.sample(subjects, 10)

        answ_filtered_course_works = []
        for course_work in course_works:
            if filter_subjects in course_work['subjects']:
                answ_filtered_course_works.append(subjects)

        answ_filtered_course_works.sort(key=lambda x: x['chat_id'])

        tasks = []
        for work in course_works:
            tasks.append(self.db.add_course_work(work))

        filtered_course_works = await self.db.get_course_works(filter_subjects)
        filtered_course_works.sort(key=lambda x: x['chat_id'])

        self.assertListEqual(filtered_course_works, answ_filtered_course_works)


def runtests():
    test_case = TestDatabaseSimple("test_initdb")
    test_case.run()
    test_case = TestDatabaseAccepted("test_initdb")
    test_case.run()
    test_case = TestDatabaseFiltered("test_initdb")
    test_case.run()
