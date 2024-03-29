import datetime
import uuid

from django.contrib.auth.models import User, Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Author, Genre, Language, Book, BookInstance


class AuthorListViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create 13 authors for pagination tests
        number_of_authors = 13
        for author_num in range(number_of_authors):
            Author.objects.create(first_name=f'Chris {author_num}', last_name=f'Sur {author_num}')

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/catalog/authors/')
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'catalog/author_list.html')

    def test_pagination_is_ten(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] is True)
        self.assertTrue(len(resp.context['author_list']) == 10)

    def test_lists_all_authors(self):
        # Confirm the second page has exactly 3 authors
        resp = self.client.get(reverse('authors') + '?page=2')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] is True)
        self.assertTrue(len(resp.context['author_list']) == 3)


def create_book():
    """Create a test book and save it to the database"""
    author = Author.objects.create(first_name='John', last_name='Smith')
    genre = Genre.objects.create(name='Fantasy')
    language = Language.objects.create(name='English')
    book = Book.objects.create(title='Book Title', summary='My book summary', isbn='ABCDEFG',
                               author=author, language=language)

    # Need to separately assign genre (many-to-many field)
    book.genre.set((genre,))
    book.save()
    return book


class LoanedBooksByUserListViewTest(TestCase):
    PASSWORD = '12345'

    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username='testuser1', password=self.PASSWORD)
        self.user2 = User.objects.create_user(username='testuser2', password=self.PASSWORD)

        # Create a book
        book = create_book()

        # Create 30 BookInstance objects
        num_book_copies = 30
        for book_copy in range(num_book_copies):
            due_date = timezone.now() + datetime.timedelta(days=book_copy % 5)
            borrower = self.user1 if book_copy % 2 else self.user2
            BookInstance.objects.create(book=book, imprint='2016', due_back=due_date,
                                        borrower=borrower, status='m')

    def test_redirect_if_not_logged_in(self):
        url = reverse('my-borrowed')
        resp = self.client.get(url)
        self.assertRedirects(resp, '/accounts/login/?next=' + url)

    def test_logged_in_uses_correct_template(self):
        self.client.login(username=self.user1.username, password=self.PASSWORD)
        resp = self.client.get(reverse('my-borrowed'))

        # Verify our user is logged in
        self.assertEqual(str(resp.context['user']), self.user1.username)
        self.assertEqual(resp.status_code, 200)

        # Verify we used the correct template
        self.assertTemplateUsed(resp, 'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        self.client.login(username=self.user1.username, password=self.PASSWORD)
        resp = self.client.get(reverse('my-borrowed'))

        # Verify our user is logged in
        self.assertEqual(str(resp.context['user']), self.user1.username)
        self.assertEqual(resp.status_code, 200)

        # We shouldn't have any books in the list initially (none on loan)
        self.assertTrue('bookinstance_list' in resp.context)
        self.assertEqual(len(resp.context['bookinstance_list']), 0)

        # Now loan some books
        for copy in BookInstance.objects.all()[:10]:
            copy.status = 'o'
            copy.save()

        # Verify the borrowed books show up in the list
        resp = self.client.get(reverse('my-borrowed'))
        self.assertTrue('bookinstance_list' in resp.context)

        # Verify that only books which belong to our user and are on loan appear
        for copy in resp.context['bookinstance_list']:
            self.assertEqual(resp.context['user'], copy.borrower)
            self.assertEqual('o', copy.status)

    def test_pages_ordered_by_due_date(self):
        # Loan all books
        for copy in BookInstance.objects.all():
            copy.status = 'o'
            copy.save()

        self.client.login(username=self.user1.username, password=self.PASSWORD)
        resp = self.client.get(reverse('my-borrowed'))

        # Verify our user is logged in
        self.assertEqual(str(resp.context['user']), self.user1.username)
        self.assertEqual(resp.status_code, 200)

        # Confirm only 10 items are displayed due to pagination
        self.assertEqual(len(resp.context['bookinstance_list']), 10)

        # Verify the books with the earliest due dates appear earlier
        last_date = 0
        for copy in BookInstance.objects.all():
            if last_date != 0:
                self.assertLessEqual(last_date, copy.due_back)
            last_date = copy.due_back


class RenewBookViewTest(TestCase):
    PASSWORD = '12345'

    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username='testuser1', password=self.PASSWORD)
        self.user2 = User.objects.create_user(username='testuser2', password=self.PASSWORD)

        # Give user2 permission to renew books
        permission = Permission.objects.get(codename='can_mark_returned')
        self.user2.user_permissions.add(permission)
        self.user2.save()

        # Create a book
        book = create_book()

        # Create book instances for user1 and user2
        due_date = datetime.date.today() + datetime.timedelta(days=5)
        self.copy1 = BookInstance.objects.create(book=book, imprint='2016', due_back=due_date,
                                                 borrower=self.user1, status='o')
        self.copy2 = BookInstance.objects.create(book=book, imprint='2016', due_back=due_date,
                                                 borrower=self.user1, status='o')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('renew-book', args=[self.copy1.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_redirect_if_logged_in_but_incorrect_permission(self):
        self.client.login(username=self.user1.username, password=self.PASSWORD)

        resp = self.client.get(reverse('renew-book', args=[self.copy1.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_login_with_permission_borrowed_book(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        # Verify we can renew our own book (we have permission)
        resp = self.client.get(reverse('renew-book', args=[self.copy2.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_login_with_permission_another_users_borrowed_book(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        # Verify we can renew any user's book (we're a librarian)
        resp = self.client.get(reverse('renew-book', args=[self.copy1.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_404_for_invalid_book_if_logged_in(self):
        fake_uuid = uuid.uuid4()
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        resp = self.client.get(reverse('renew-book', args=[fake_uuid]))
        self.assertEqual(resp.status_code, 404)

    def test_uses_correct_template(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)
        resp = self.client.get(reverse('renew-book', args=[self.copy1.pk]))
        self.assertEqual(resp.status_code, 200)

        # Verify we used the correct template
        self.assertTemplateUsed(resp, 'catalog/book_renew.html')

    def test_form_renewal_date_initially_three_weeks_in_future(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)
        resp = self.client.get(reverse('renew-book', args=[self.copy1.pk]))
        self.assertEqual(resp.status_code, 200)

        date_3_weeks_in_future = datetime.date.today() + datetime.timedelta(weeks=3)
        self.assertEqual(resp.context['form'].initial['renewal_date'], date_3_weeks_in_future)

    def test_redirects_to_all_borrowed_books_list_on_success(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        valid_date = datetime.date.today() + datetime.timedelta(weeks=2)
        resp = self.client.post(reverse('renew-book', args=[self.copy1.pk]),
                                {'renewal_date': valid_date})
        self.assertRedirects(resp, reverse('all-borrowed'))

    def test_form_invalid_renewal_date_past(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        past_date = datetime.date.today() - datetime.timedelta(weeks=1)
        resp = self.client.post(reverse('renew-book', args=[self.copy1.pk]),
                                {'renewal_date': past_date})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'renewal_date',
                             'Invalid date - renewal cannot be in the past')

    def test_form_invalid_renewal_date_future(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        invalid_future_date = datetime.date.today() + datetime.timedelta(weeks=5)
        resp = self.client.post(reverse('renew-book', args=[self.copy1.pk]),
                                {'renewal_date': invalid_future_date})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp, 'form', 'renewal_date',
                             'Invalid date - renewal cannot exceed 4 weeks')


class AuthorCreateViewTest(TestCase):
    PASSWORD = '12345'

    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username='testuser1', password=self.PASSWORD)
        self.user2 = User.objects.create_user(username='testuser2', password=self.PASSWORD)

        # Give user2 permission to create new books
        permission = Permission.objects.get(name='Can add author')
        self.user2.user_permissions.add(permission)
        self.user2.save()

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('author_create'))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_correct_login_but_incorrect_permission(self):
        self.client.login(username=self.user1.username, password=self.PASSWORD)

        resp = self.client.get(reverse('author_create'))
        self.assertEqual(resp.status_code, 403)

    def test_login_with_permission_can_see_view(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        resp = self.client.get(reverse('author_create'))
        self.assertEqual(resp.status_code, 200)

    def test_uses_correct_template(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)
        resp = self.client.get(reverse('author_create'))
        self.assertEqual(resp.status_code, 200)

        # Verify we used the correct template
        self.assertTemplateUsed(resp, 'catalog/author_form.html')

    def test_redirects_to_author_resource_on_success(self):
        self.client.login(username=self.user2.username, password=self.PASSWORD)

        resp = self.client.post(reverse('author_create'), {
            'first_name': 'John',
            'last_name': 'Smith',
            'date_of_birth': '2018-08-09',
            'date_of_death': '',
        })
        self.assertRedirects(resp, '/catalog/author/1')
