from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.forms import UserCreationForm 
from django.contrib import messages
from django.contrib.auth import authenticate,logout
from django.contrib.auth.decorators import login_required
from .models import Syllabus, Notes
from django.core.files.storage import default_storage
from .forms import SyllabusForm
import google.generativeai as genai
from django.conf import settings
from .models import Quizzes


# Create your views here.
def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request,f"Account created for {username}!")
            return redirect('login')
        else:
            print(form.errors)  
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form':form})



def custom_logout(request):
    logout(request)
    return render(request,'logout.html')


@login_required
def syllabus_input(request):
    if request.method == "POST":
        syllabus_content = request.POST.get("syllabus")

        # Configure Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)

        try:
            # Use Gemini 1.5 Flash (2.0 Flash)
            model = genai.GenerativeModel('gemini-2.0-flash')

            # Save syllabus
            syllabus = Syllabus.objects.create(user=request.user, content=syllabus_content)

            # === Generate Notes ===
            notes_prompt = f"""
You are a professional academic tutor helping a student prepare for their exams.
Generate concise study notes strictly based on the following SYLLABUS:
{syllabus_content}

Keep the tone student-friendly and focused on helping them grasp the material efficiently.
"""
            notes_response = model.generate_content(notes_prompt)
            notes_content = notes_response.text
            Notes.objects.create(syllabus=syllabus, content=notes_content)

            # === Generate Quiz ===
    
            quiz_prompt = f"""
            Generate 5 multiple-choice quiz questions based on:
            {syllabus_content}

            Format each question like this:
            Question: [question text]
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            Answer: [correct option letter]
            """
            quiz_response = model.generate_content(quiz_prompt)
            quiz_text = quiz_response.text

            for block in quiz_text.strip().split("\n\n"):
                if "Question:" in block:
                    lines = [line.strip() for line in block.split("\n") if line.strip()]
                    question = lines[0].replace("Question: ", "")
                    options = {
            'A': lines[1][3:],  # Remove "A) " prefix
            'B': lines[2][3:],  # Remove "B) " prefix
            'C': lines[3][3:],  # Remove "C) " prefix
            'D': lines[4][3:]   # Remove "D) " prefix
        }
        
                    answer = lines[5].replace("Answer: ", "").strip().upper()[0]  # Just the letter

                    Quizzes.objects.create(
                        syllabus=syllabus,
                        question=question,
                        options={"options": options},
                        answer=answer
                    )

            messages.success(request, "Notes and quiz generated successfully!")
            return redirect('notes')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('syllabus_input')

    return render(request, 'syllabus_input.html')


       

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notes

@login_required
def notes(request):
    # Order by creation time descending so newest notes come first
    notes_list = Notes.objects.filter(syllabus__user=request.user).order_by('-created_at')
    return render(request, 'notes.html', {'notes': notes_list})

from collections import defaultdict
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Quizzes

@login_required
def quiz(request):
    quizzes = Quizzes.objects.filter(syllabus__user=request.user).select_related('syllabus').order_by('-created_at')
    
    results = {}
    submitted = False
    submitted_syllabus_id = None

    if request.method == "POST":
        submitted = True
        submitted_syllabus_id = request.POST.get("syllabus_id")

        syllabus_quizzes = quizzes.filter(syllabus__id=submitted_syllabus_id)

        for quiz in syllabus_quizzes:
            selected = request.POST.get(f"question_{quiz.id}")
            if selected:
                results[quiz.id] = {
                    'selected': selected,
                    'is_correct': selected == quiz.answer,
                    'correct_answer': quiz.answer,
                    'options': quiz.options['options']
                }

    syllabus_quizzes_grouped = defaultdict(list)
    for quiz in quizzes:
        syllabus_quizzes_grouped[quiz.syllabus].append(quiz)

    return render(request, 'quiz.html', {
        'syllabus_quizzes': dict(syllabus_quizzes_grouped),
        'submitted': submitted,
        'submitted_syllabus_id': submitted_syllabus_id,
        'results': results
    })
