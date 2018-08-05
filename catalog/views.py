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

    context = {
        'num_books': num_books,
        'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors,
        'num_genres': num_genres,
        'num_dog_books': num_dog_books,
    }

    # Render the HTML template with the data in the context variable
    return render(request, 'index.html', context)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 10


class BookDetailView(generic.DetailView):
    model = Book
