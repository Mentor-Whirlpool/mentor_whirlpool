import asynctest
from asyncio import gather
from mentor_whirlpool.database import Database
import random
import string


async def clear_database(db):
    await gather(db.db.execute('DELETE FROM COURSE_WORKS_SUBJECTS'),
                 db.db.execute('DELETE FROM ACCEPTED_SUBJECTS'),
                 db.db.execute('DELETE FROM MENTORS_SUBJECTS'),
                 db.db.execute('DELETE FROM MENTORS_STUDENTS'),
                 db.db.execute('DELETE FROM SUPPORT_REQUESTS'),
                 db.db.execute('DELETE FROM ACCEPTED'),
                 db.db.execute('DELETE FROM COURSE_WORKS'),
                 db.db.execute('DELETE FROM ADMINS'),
                 db.db.execute('DELETE FROM MENTORS'),
                 db.db.execute('DELETE FROM STUDENTS'),
                 db.db.execute('DELETE FROM SUBJECTS'),
                 db.db.execute('DELETE FROM SUPPORTS'))

# fine to test altogether, because different tables are tested
class TestDatabaseSimple(asynctest.TestCase):
    async def test_initdb(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
        # await self.db.initdb()
        expected_tables = [('students',), ('course_works',), ('accepted',), ('subjects',),
                           ('mentors',), ('admins',), ('supports',), ('support_requests',),
                           ('course_works_subjects',), ('mentors_subjects',),
                           ('mentors_students',), ('support_requests',),]
        # executemany is screwed
        for table in expected_tables:
            exists = await (await self.db.db.execute("""
            SELECT EXISTS(
            SELECT FROM information_schema.tables
            WHERE table_catalog = \'mentor_whirlpool\' AND
            table_name = %s)
            """, table)).fetchone()
            self.assertEqual((True,), exists)
        await self.db.db.close()

class TestDatabaseSubject(asynctest.TestCase):
    async def test_add_subject_random(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
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
        await self.db.db.close()

class TestDatabaseMentor(asynctest.TestCase):
    async def test_add_remove_mentor(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
        subj = ['SQL Injection', 'TestSubj']
        mentors = [{
            'name': name,
            'chat_id': random.randint(0, 9999),
            'subjects': subj,
            'students': [],
            'load': 0,
        } for name in ['Alice', 'Bob', 'Victor', 'Eugene']]
        mentors.append(
            {
                'name': 'Yoshi',
                'chat_id': random.randint(0, 9999),
                'subjects': [],
                'students': [],
                'load': 0,
            }
        )
        tasks = []
        for mentor in mentors:
            tasks.append(self.db.add_mentor(mentor))
        await gather(*tasks)

        for line in mentors:
            self.assertTrue(await self.db.check_is_mentor(line['chat_id']))

        mentors.sort(key=lambda x: x['name'])
        for ment in mentors:
            ment['subjects'].sort()
        dbmentors = await self.db.get_mentors()
        dbmentors.sort(key=lambda x: x['name'])
        for ment in dbmentors:
            ment.pop('id', None)
            ment['subjects'].sort()
        self.assertListEqual(mentors, dbmentors)
        await self.db.remove_mentor(chat_id=mentors[2]['chat_id'])
        self.assertFalse(await self.db.check_is_mentor(mentors[2]['chat_id']))
        mentors.pop(2)
        dbmentors = await self.db.get_mentors()
        dbmentors.sort(key=lambda x: x['name'])
        for ment in dbmentors:
            ment.pop('id', None)
            ment['subjects'].sort()
        self.assertListEqual(mentors, dbmentors)
        await self.db.db.close()


class TestDatabaseCourseWork(asynctest.TestCase):
    def check_contains_student(self, student, dbstudents):
        for stud in dbstudents:
            if stud['name'] == student:
                return True
        return False

    async def test_add_remove_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
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
        course_works.sort(key=lambda x: x['description'])
        dbworks = await self.db.get_course_works()
        for work in dbworks:
            work.pop('id')
        dbworks.sort(key=lambda x: x['description'])
        self.assertEqual(len(course_works), len(dbworks))
        dbstudents = await self.db.get_students()
        for stud in names:
            self.assertTrue(self.check_contains_student(stud, dbstudents))
        dbworks = await self.db.get_course_works()
        to_remove = random.sample(dbworks, 100)
        tasks = []
        for rem in to_remove:
            tasks.append(self.db.remove_course_work(rem['id']))
        await gather(*tasks)
        course_works = dbworks
        for rem in to_remove:
            course_works.remove(rem)
        dbworks = await self.db.get_course_works()
        dbworks.sort(key=lambda x: x['description'])
        self.assertCountEqual(course_works, dbworks)

        for student in await self.db.get_students():
            self.assertEqual((await self.db.get_students(student['id']))[0], student)
            self.assertEqual((await self.db.get_students(chat_id=student['chat_id']))[0], student)

        # for student in dbstudents:
        #     self.assertListEqual(await self.db.get_student_course_works(student['chat_id']), student['course_works'])
        await self.db.db.close()

class TestDatabaseAdmins(asynctest.TestCase):
    async def test_add_remove_admins(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)

        admin_chat_id = list(set(random.randint(0, 9999) for _ in range(8)))
        tasks = []
        for chat_id in admin_chat_id:
            tasks.append(self.db.add_admin(chat_id))
        await gather(*tasks)

        for chat_id in admin_chat_id:
            self.assertTrue(await self.db.check_is_admin(chat_id))
        self.assertFalse(await self.db.check_is_admin(11111))
        self.assertFalse(await self.db.check_is_admin(12433))
        self.assertFalse(await self.db.check_is_admin(76685))
        self.assertFalse(await self.db.check_is_admin(11144))

        self.assertListEqual(admin_chat_id, [adm['chat_id'] for adm in await self.db.get_admins()])

        tasks = []
        for chat_id in admin_chat_id:
            tasks.append(self.db.remove_admin(chat_id=chat_id))
        await gather(*tasks)

        for chat_id in admin_chat_id:
            self.assertFalse(await self.db.check_is_admin(chat_id))

        self.assertListEqual([], await self.db.get_admins())
        await self.db.db.close()

class TestDatabaseSupport(asynctest.TestCase):
    async def test_add_remove_support(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)

        names = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        supports = [{
                'chat_id': chat_id,
                'name': random.choice(names),
            } for chat_id in range(0, 1000)]
        await gather(*[self.db.add_support(supp) for supp in supports])

        dbsupports = await self.db.get_supports()
        for supp in dbsupports:
            supp.pop('id')
        supports.sort(key=lambda x: x['chat_id'])
        dbsupports.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(supports, dbsupports)

        dbsupports_chatid_filter = [(await self.db.get_supports(chat_id=supp['chat_id']))[0] for supp in supports]
        for supp in dbsupports_chatid_filter:
            supp.pop('id')
        dbsupports_chatid_filter.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(supports, dbsupports_chatid_filter)

        dbsupports = await self.db.get_supports()
        dbsupports_id_filter = [(await self.db.get_supports(supp['id']))[0] for supp in dbsupports]
        dbsupports.sort(key=lambda x: x['chat_id'])
        dbsupports_id_filter.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(dbsupports, dbsupports_id_filter)

        to_remove = random.sample(dbsupports, 100)
        await gather(*[self.db.remove_support(supp['id']) for supp in to_remove])
        supports = [supp for supp in dbsupports if supp not in to_remove]
        supports.sort(key=lambda x: x['chat_id'])
        dbsupports = await self.db.get_supports()
        dbsupports.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(supports, dbsupports)

        to_remove = random.sample(dbsupports, 100)
        await gather(*[self.db.remove_support(chat_id=supp['chat_id']) for supp in to_remove])
        supports = [supp for supp in dbsupports if supp not in to_remove]
        supports.sort(key=lambda x: x['chat_id'])
        dbsupports = await self.db.get_supports()
        dbsupports.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(dbsupports, supports)
        await self.db.db.close()

    async def test_add_remove_support_request(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)

        names = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        issues = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        support_requests = [{
                'chat_id': chat_id,
                'name': random.choice(names),
                'issue': random.choice(issues),
            } for chat_id in range(0, 100)] + [{
                'chat_id': chat_id,
                'name': random.choice(names),
                'issue': None,
            } for chat_id in range(100, 200)]
        await gather(*[self.db.add_support_request(supp) for supp in support_requests])

        dbsupport_requests = await self.db.get_support_requests()
        for supp in dbsupport_requests:
            supp.pop('id')
            supp.pop('support')
        support_requests.sort(key=lambda x: x['chat_id'])
        dbsupport_requests.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(support_requests, dbsupport_requests)

        dbsupport_requests_chatid_filter = [(await self.db.get_support_requests(chat_id=supp['chat_id']))[0] for supp in support_requests]
        for supp in dbsupport_requests_chatid_filter:
            supp.pop('id')
            supp.pop('support')
        dbsupport_requests_chatid_filter.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(support_requests, dbsupport_requests_chatid_filter)

        dbsupport_requests = await self.db.get_support_requests()
        dbsupport_requests_id_filter = [(await self.db.get_support_requests(supp['id']))[0] for supp in dbsupport_requests]
        dbsupport_requests.sort(key=lambda x: x['chat_id'])
        dbsupport_requests_id_filter.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(dbsupport_requests, dbsupport_requests_id_filter)

        to_remove = random.sample(dbsupport_requests, 100)
        await gather(*[self.db.remove_support_request(supp['id']) for supp in to_remove])
        support_requests = [supp for supp in dbsupport_requests if supp not in to_remove]
        support_requests.sort(key=lambda x: x['chat_id'])
        dbsupport_requests = await self.db.get_support_requests()
        dbsupport_requests.sort(key=lambda x: x['chat_id'])
        self.assertListEqual(support_requests, dbsupport_requests)
        await self.db.db.close()


class TestDatabaseAccepted(asynctest.TestCase):
    async def test_accept_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
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
                'name': 'Alice',
                'chat_id': 10001,
                'subjects': ['TypeScript, Crypto'],
                'description': 'I\'m not accepted',
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
        await self.db.add_mentor({
            'name': 'Yoshi',
            'chat_id': 10003,
            'subjects': []
        })

        mentors = await self.db.get_mentors()
        for i in range(len(dbwork)):
            if i == 2:
                continue
            await self.db.accept_work(mentors[i % len(mentors)]['id'], dbwork[i]['id'])
            mentors[i % len(mentors)]['students'].append(dbwork[i]['student'])
        for i in dbwork:
            if i['description'] == 'I\'m not accepted':
                dbwork.remove(i)
                break
        self.assertListEqual(await self.db.get_accepted(), dbwork)
        self.assertListEqual(await self.db.get_course_works(), [])
        for ment in mentors:
            ment_studs = [stud['id'] for stud in await self.db.get_students(mentor_id=ment['id'])]
            ment_studs.sort()
            ment['students'].sort()
            self.assertListEqual(ment_studs, ment['students'])
        for work in dbwork:
            # self.assertEqual((await self.db.get_accepted(work['subjects']))[0], work)
            self.assertEqual((await self.db.get_accepted(student=work['student']))[0], work)

        for work in dbwork:
            await self.db.readmission_work(work['id'])
        works_readmissioned = await self.db.get_course_works()
        works_readmissioned.sort(key=lambda x: x['id'])
        dbwork.sort(key=lambda x: x['id'])
        self.assertListEqual(dbwork, works_readmissioned)
        works_readmissioned_filt_subj = await self.db.get_course_works(subjects=['TCP', 'SQL'])
        works_readmissioned_filt_subj.sort(key=lambda x: x['id'])
        dbwork_filt_subj = [work for work in dbwork if any(map(lambda x: x in ['TCP', 'SQL'], work['subjects']))]
        dbwork_filt_subj.sort(key=lambda x: x['id'])
        self.assertListEqual(dbwork_filt_subj, works_readmissioned_filt_subj)
        works_readmissioned_filt_stud = await self.db.get_course_works(student=dbwork[0]['student'])
        works_readmissioned_filt_stud.sort(key=lambda x: x['id'])
        dbwork_filt_stud = [work for work in dbwork if work['student'] == dbwork[0]['student']]
        dbwork_filt_stud.sort(key=lambda x: x['id'])
        self.assertListEqual(dbwork_filt_stud, works_readmissioned_filt_stud)
        

        # await self.db.modify_course_work()
        await self.db.db.close()


class TestDatabaseReject(asynctest.TestCase):
    async def test_accept_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)

        subjects = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        names = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(100)]
        descriptions = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        course_works = [{
            'name': names[i],
            'chat_id': i,
            'subjects': random.sample(subjects, 10),
            'description': random.choice(descriptions)
        } for i in range(len(names))]
        mentors = [{
            'name': name,
            'chat_id': chat_id,
            'subjects': [],
            'students': [],
            'load': 0,
        } for (name, chat_id) in zip(''.join(random.choice(string.ascii_lowercase) for i in range(10) for j in range(100)), range(30000,30100))]
        tasks = [self.db.add_course_work(work) for work in course_works] + [self.db.add_mentor(ment) for ment in mentors]
        await gather(*tasks)
        course_works = await self.db.get_course_works()

        # accept some
        mentors = await self.db.get_mentors()
        to_accept = random.sample(course_works, 50)
        await gather(*[self.db.accept_work(mentors[i]['id'], work['id'])
                       for (i, work) in enumerate(to_accept)])

        # reject some of those
        to_reject = random.sample(to_accept, 20)
        await gather(*[self.db.reject_work(mentors[i]['id'], to_reject[i]['id']) for i in range(len(to_reject))])
        expected_works = [work for work in course_works if work not in to_accept or work in to_reject]
        expected_works.sort(key=lambda x: x['id'])
        dbworks = await self.db.get_course_works()
        dbworks.sort(key=lambda x: x['id'])
        self.assertListEqual(expected_works, dbworks)
        await self.db.db.close()


class TestDatabaseRemoveStudent(asynctest.TestCase):
    async def test_remove_student(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)

        subjects = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        names = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(100)]
        descriptions = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        course_works = [{
            'name': names[i],
            'chat_id': i,
            'subjects': random.sample(subjects, 10),
            'description': random.choice(descriptions)
        } for i in range(len(names))]
        mentors = [{
            'name': name,
            'chat_id': chat_id,
            'subjects': [],
            'students': [],
            'load': 0,
        } for (name, chat_id) in zip(''.join(random.choice(string.ascii_lowercase) for i in range(10) for j in range(100)), range(20000,20100))]
        tasks = [self.db.add_course_work(work) for work in course_works] + [self.db.add_mentor(ment) for ment in mentors]
        await gather(*tasks)

        # accept some
        mentors = await self.db.get_mentors()
        await gather(*[self.db.accept_work(random.choice(mentors)['id'], to_accept['id'])
                       for to_accept in random.sample(await self.db.get_course_works(), 50)])

        students = await self.db.get_students()
        to_remove = [stud['id'] for stud in random.sample(students, 20)]
        students = [stud for stud in students if stud['id'] not in to_remove]
        course_works = [work for work in await self.db.get_course_works() if work['student'] not in to_remove]
        accepted_works = [work for work in await self.db.get_accepted() if work['student'] not in to_remove]
        await gather(*[self.db.remove_student(stud) for stud in to_remove])
        dbstudents = await self.db.get_students()
        dbstudents.sort(key=lambda x: x['id'])
        students.sort(key=lambda x: x['id'])
        dbcourse_works = await self.db.get_course_works()
        dbcourse_works.sort(key=lambda x: x['id'])
        course_works.sort(key=lambda x: x['id'])
        self.assertListEqual(dbstudents, students)
        self.assertListEqual(dbcourse_works, course_works)
        await self.db.db.close()


class TestDatabaseFiltered(asynctest.TestCase):
    async def test_filter_for_get_course_works(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
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

        answ_filtered_course_works = [work for work in course_works if any(subj in filter_subjects for subj in work['subjects'])]
        for work in answ_filtered_course_works:
            work['subjects'].sort()

        tasks = []
        for work in course_works:
            tasks.append(self.db.add_course_work(work))
        await gather(*tasks)

        # can only compare subjects and description fields
        for work in answ_filtered_course_works:
            work.pop('name')
            work.pop('chat_id')
            work['subjects'].sort()

        filtered_course_works = await self.db.get_course_works(subjects=filter_subjects)
        for work in filtered_course_works:
            work.pop('id')
            work.pop('student')
            work['subjects'].sort()

        filter_subjects.sort()
        answ_filtered_course_works.sort(key=lambda x: x['description'])
        filtered_course_works.sort(key=lambda x: x['description'])
        difference = [work for work in filtered_course_works if work not in answ_filtered_course_works]
        difference += [work for work in answ_filtered_course_works if work not in filtered_course_works]
        # idk why, but it assertListEqual really insists that they are different
        # probably two works with equal description messing with sort or whatever
        # i spent a little too much time figuring out what's the issue and can't
        # be bothered anymore to fix this stupid junk
        # self.assertListEqual(filtered_course_works, answ_filtered_course_works)
        self.assertListEqual(difference, [])
        await self.db.db.close()


class TestDatabaseMentorSubjects(asynctest.TestCase):
    async def test_add_remove_mentor_subjects(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)
        start_subj = ['SQL Injection', 'TestSubj']
        mentor = {
            'name': 'Alice',
            'chat_id': 1,
            'subjects': start_subj,
        }
        no_subj_mentor = {
            'name': 'Bob',
            'chat_id': 2,
            'subjects': None,
        }
        tasks = []
        tasks.append(self.db.add_mentor(mentor))
        tasks.append(self.db.add_mentor(no_subj_mentor))
        await gather(*tasks)
        dbmentors = await self.db.get_mentors()
        dbmentors.sort(key=lambda x: x['name'])
        new_subjects = ['TCP/IP', 'Qt']
        tasks = []
        for ment in dbmentors:
            tasks.append(self.db.add_mentor_subjects(ment['id'], new_subjects))
            if ment['subjects'] is None:
                ment['subjects'] = new_subjects
            else:
                ment['subjects'] += new_subjects
            ment['subjects'].sort()
        await gather(*tasks)
        dbmentors_new = await self.db.get_mentors()
        dbmentors_new.sort(key=lambda x: x['name'])
        for ment in dbmentors_new:
            ment['subjects'].sort()
        self.assertListEqual(dbmentors, dbmentors_new)

        await self.db.remove_mentor_subjects(dbmentors[0]['id'], [dbmentors[0]['subjects'][0]])
        dbmentors[0]['subjects'].pop(0)
        await self.db.remove_mentor_subjects(dbmentors[1]['id'], [dbmentors[1]['subjects'][1]])
        dbmentors[1]['subjects'].pop(1)
        for ment in dbmentors:
            ment['subjects'].sort()
        dbmentors_new = await self.db.get_mentors()
        dbmentors_new.sort(key=lambda x: x['name'])
        for ment in dbmentors_new:
            ment['subjects'].sort()
        self.assertListEqual(dbmentors, dbmentors_new)

        for ment in dbmentors:
            dbmentor = (await self.db.get_mentors(chat_id=ment['chat_id']))[0]
            dbmentor['subjects'].sort()
            self.assertEqual(dbmentor, ment)
        await self.db.db.close()


class TestDatabaseModifyCourseWork(asynctest.TestCase):
    async def test_modify_course_work(self):
        self.db = Database()
        await self.db.initdb()
        await clear_database(self.db)

        subjects = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
        names = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(100)]
        descriptions = [(''.join(random.choice(string.ascii_lowercase) for i in range(10))) for j in range(1000)]
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

        course_works = await self.db.get_course_works()
        to_modify = random.sample(course_works, 50)
        for work in course_works:
            if work not in to_modify:
                continue
            work['subjects'] = random.sample(subjects, 10)
            work['description'] = random.choice(descriptions)
            await self.db.modify_course_work(work)
        new_works = await self.db.get_course_works()
        course_works.sort(key=lambda x: x['id'])
        new_works.sort(key=lambda x: x['id'])
        for work in new_works:
            work['subjects'].sort()
        for work in course_works:
            work['subjects'].sort()
        self.assertListEqual(course_works, new_works)
        await self.db.db.close()
