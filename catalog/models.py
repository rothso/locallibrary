import uuid

from django.db import models
from django.urls import reverse


class Genre(models.Model):
    """Model representing a book genre"""
    name = models.CharField(max_length=200, help_text='Enter a book genre (e.g. Science Fiction)')

    def __str__(self):
        """String for representing the genre object"""
        return self.name


class Book(models.Model):
    """Model representing a book definition (but not an actual copy of a book)"""
    title = models.CharField(max_length=200)
    author = models.ForeignKey('Author', on_delete=models.SET_NULL, null=True)
    summary = models.TextField(max_length=1000, help_text='Enter a brief description of the book')
    isbn = models.CharField('ISBN', max_length=13, help_text='13 Character ISBN number')
    genre = models.ManyToManyField(Genre, help_text="Select a genre for this book")

    def __str__(self):
        """String for representing the book object"""
        return self.title

    def get_absolute_url(self):
        """Returns the URL to access a detailed record for this book"""
        return reverse('book-detail', args=[str(self.id)])


class BookInstance(models.Model):
    """Model representing a copy of a book (i.e. that can be borrowed)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4(), help_text='Unique in-library ID')
    book = models.ForeignKey(Book, on_delete=models.SET_NULLA, null=True)
    imprint = models.CharField(max_length=200)
    due_back = models.DateField(null=True, blank=True)

    LOAN_STATUS = (
        ('m', 'Maintenance'),
        ('o', 'On loan'),
        ('a', 'Available'),
        ('r', 'Reserved'),
    )

    status = models.CharField(
        max_length=1,
        choices=LOAN_STATUS,
        blank=True,
        default='m',
        help_text='Book availability'
    )

    class Meta:
        ordering = ['due_back']

    def __str__(self):
        """String for representing the book instance object"""
        return f'{self.id} ({self.book.title})'
