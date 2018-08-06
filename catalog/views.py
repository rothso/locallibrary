from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.views import generic

from .models import Author, Book, BookInstance, Genre


def index(request):
    """"View for homepage of the site"""

    # Generate counts of some of the main objects
    num_books = Book.objects.count()
    num_instances = BookInstance.objects.count()
    num_authors = Author.objects.count()
    num_genres = Genre.objects.count()

    # Available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()

    # Books about dogs
    num_dog_books = Book.objects.filter(title__icontains='dog').count()

    # Number of visits by this user, as counted in the session variable
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_dog_books': num_dog_books,
        'num_visits': num_visits,
    }

    # Render the HTML template with the data in the context variable
    return render(request, 'index.html', context)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10


class BookDetailView(generic.DetailView):
    model = Book


class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10


class AuthorDetailView(generic.DetailView):
    model = Author


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """Generic class-based view listing books on loan to current user"""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return (BookInstance.objects
                .filter(borrower=self.request.user)
                .filter(status__exact='o')
                .order_by('due_back'))


class AllLoanedBooksListView(PermissionRequiredMixin, generic.ListView):
    """Allows librarians to view all books on loan"""
    model = BookInstance
    template_name = 'catalog/bookinstance_list_all.html'
    paginate_by = 10

    # Only librarians can access this page
    permission_required = 'catalog.can_mark_returned'
