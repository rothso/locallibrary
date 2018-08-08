import datetime

from django.contrib.auth.models import User
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


class LoanedBooksByUserListViewTest(TestCase):
    PASSWORD = '12345'

    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username='testuser1', password=self.PASSWORD)
        self.user2 = User.objects.create_user(username='testuser2', password=self.PASSWORD)

        # Create a book
        author = Author.objects.create(first_name='John', last_name='Smith')
        genre = Genre.objects.create(name='Fantasy')
        language = Language.objects.create(name='English')
        book = Book.objects.create(title='Book Title', summary='My book summary', isbn='ABCDEFG',
                                   author=author, language=language)

        # Need to separately assign genre (many-to-many field)
        book.genre.set((genre,))
        book.save()

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
