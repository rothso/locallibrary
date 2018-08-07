import datetime

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .forms import RenewBookForm
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


@permission_required('catalog.can_mark_returned')
def renew_book(request, pk):
    book_instance = get_object_or_404(BookInstance, pk=pk)

    if request.method == 'POST':
        # Bind the form to the data from the request
        form = RenewBookForm(request.POST)

        if form.is_valid():
            # Write the data to the model and save it to the database
            book_instance.due_back = form.cleaned_data['renewal_date']
            book_instance.save()
            return HttpResponseRedirect(reverse('all-borrowed'))
    else:
        # Create an unbound form with a suggested renewal date
        proposed_renew_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookForm(initial={'renewal_date': proposed_renew_date})

    return render(request, 'catalog/book_renew.html', {'form': form, 'bookinst': book_instance})


class AuthorCreate(PermissionRequiredMixin, CreateView):
    model = Author
    fields = '__all__'
    permission_required = 'catalog.add_author'


class AuthorUpdate(PermissionRequiredMixin, UpdateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']
    permission_required = 'catalog.change_author'


class AuthorDelete(PermissionRequiredMixin, DeleteView):
    model = Author
    success_url = reverse_lazy('authors')
    permission_required = 'catalog.delete_author'
