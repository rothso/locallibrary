from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('books/', views.BookListView.as_view(), name='books'),
    path('books/my', views.LoanedBooksByUserListView.as_view(), name='my-borrowed'),
    path('book/<int:pk>', views.BookDetailView.as_view(), name='book-detail'),
    path('authors/', views.AuthorListView.as_view(), name='authors'),
    path('author/<int:pk>', views.AuthorDetailView.as_view(), name='author-detail'),

    # Librarian-only paths
    path('borrowed/', views.AllLoanedBooksListView.as_view(), name='all-borrowed'),
    path('book/<uuid:pk>/renew/', views.renew_book, name='renew-book')
]
