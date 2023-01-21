from django.shortcuts import render


def index(request):  # Render the requested template for the client
    return render(request, "serverSocket/index.html")
