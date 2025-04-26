from django.shortcuts import render, redirect, HttpResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import Syllabus, Notes
from django.core.files.storage import default_storage
from .forms import SyllabusForm, UserRegistrationForm, EmailOrUsernameAuthenticationForm
import google.generativeai as genai
from django.conf import settings
from .models import Quizzes
import re
from collections import defaultdict


# Create your views here.
def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"Account created for {username}! You can now login.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = EmailOrUsernameAuthenticationForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data.get('username_or_email')
            password = form.cleaned_data.get('password')
            
            # Check if input is an email
            if '@' in username_or_email:
                try:
                    user = User.objects.get(email=username_or_email)
                    username = user.username
                except User.DoesNotExist:
                    user = None
                    username = username_or_email  # This will fail authenticate
            else:
                username = username_or_email
            
            # Authenticate with username
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username/email or password.")
    else:
        form = EmailOrUsernameAuthenticationForm()
    
    return render(request, 'login.html', {'form': form})


def custom_logout(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return render(request, 'logout.html')


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

            # === Generate Notes with improved prompt ===
            notes_prompt = f"""
            You are a professional academic tutor helping a student prepare for their exams.
            Generate comprehensive study notes based on the following SYLLABUS:
            {syllabus_content}

            Please format your response in Markdown with the following:
            1. Use clear headings (##) and subheadings (###) to organize topics
            2. Use bullet points or numbered lists for key points
            3. **Bold** important concepts and definitions
            4. Include tables where appropriate to compare and contrast concepts
            5. Create visual separation between topics with horizontal rules (---)
            6. Use code blocks for any formulas or specialized notation
            7. Organize content in a logical learning sequence
            
            Keep the tone student-friendly, clear and focused on helping them master the material efficiently.
            The notes should be concise but thorough enough to cover the main concepts.
            """
            notes_response = model.generate_content(notes_prompt)
            notes_content = notes_response.text
            Notes.objects.create(syllabus=syllabus, content=notes_content)

            # === Generate Quiz ===
            quiz_prompt = f"""
            Generate 5 multiple-choice quiz questions based on:
            {syllabus_content}

            Format each question like this EXACTLY:
            Question: [question text]
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            Answer: [correct option letter]

            Make sure to maintain this exact format for each question.
            """
            quiz_response = model.generate_content(quiz_prompt)
            quiz_text = quiz_response.text

            # More robust parsing logic
            question_blocks = re.split(r'\n\s*\n', quiz_text.strip())
            
            for block in question_blocks:
                lines = [line.strip() for line in block.split('\n') if line.strip()]
                if len(lines) < 6:  # We need at least a question, 4 options, and an answer
                    continue
                    
                # Find the question line
                question_line = next((line for line in lines if line.startswith('Question:')), None)
                if not question_line:
                    continue
                
                question = question_line.replace('Question:', '').strip()
                
                # Find the options
                option_pattern = re.compile(r'^([A-D])\)\s+(.+)$')
                options = {}
                
                for line in lines:
                    match = option_pattern.match(line)
                    if match:
                        letter, text = match.groups()
                        options[letter] = text
                
                # If we don't have all 4 options, skip this question
                if len(options) != 4:
                    continue
                
                # Find the answer line
                answer_line = next((line for line in lines if line.startswith('Answer:')), None)
                if not answer_line:
                    continue
                    
                answer = answer_line.replace('Answer:', '').strip().upper()[0]  # Just take the first letter (A, B, C, D)
                
                # Create the quiz
                if question and options and answer in "ABCD":
                    Quizzes.objects.create(
                        syllabus=syllabus,
                        question=question,
                        options={"options": options},
                        answer=answer
                    )

            messages.success(request, "Notes and quizzes generated successfully!")
            return redirect('notes')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('syllabus_input')

    return render(request, 'syllabus_input.html')


@login_required
def notes(request):
    # Order by creation time descending so newest notes come first
    notes_list = Notes.objects.filter(syllabus__user=request.user).order_by('-created_at')
    return render(request, 'notes.html', {'notes': notes_list})


@login_required
def quiz(request):
    quizzes = Quizzes.objects.filter(syllabus__user=request.user).select_related('syllabus').order_by('-created_at')
    
    # Debug output
    print(f"Found {quizzes.count()} quizzes for user {request.user}")
    
    results = {}
    submitted = False
    submitted_syllabus_id = None

    if request.method == "POST":
        submitted = True
        submitted_syllabus_id = request.POST.get("syllabus_id")

        syllabus_quizzes = quizzes.filter(syllabus__id=submitted_syllabus_id)
        
        # Debug output
        print(f"Processing submission for syllabus {submitted_syllabus_id}")
        print(f"Found {syllabus_quizzes.count()} quizzes for this syllabus")

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

    context = {
        'syllabus_quizzes': dict(syllabus_quizzes_grouped),
        'submitted': submitted,
        'submitted_syllabus_id': submitted_syllabus_id,
        'results': results
    }
    
    # Debug output
    print(f"Syllabus quizzes grouped: {len(syllabus_quizzes_grouped)} syllabi")
    
    return render(request, 'quiz.html', context)
