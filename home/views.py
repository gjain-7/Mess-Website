from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.files import File
from django.core.files.storage import default_storage
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount
from home.models import (
    About,
    Update,
    Carousel,
    Rule,
    ShortRebate,
    Caterer,
    Form,
    Cafeteria,
    Contact,
    Rebate,
    Student,
    LongRebate,
    UnregisteredStudent,
    PeriodAutumn22,
    AllocationAutumn22,
    RebateAutumn22,
    PeriodSpring23,
    AllocationSpring23,
    RebateSpring23,
    PeriodAutumn23,
    AllocationAutumn23,
    RebateAutumn23,
)
from .utils.get_rebate_bills import get_rebate_bills
from .utils.rebate_checker import (
    count,
    is_present_autumn,
    is_present_spring,
    check_rebate_autumn,
    check_rebate_spring,
    is_not_duplicate,
)
import pandas as pd
from datetime import date, timedelta
import io
from django.utils.dateparse import parse_date
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse

# Create your views here.


def home(request):
    """
    Display the Home Page :model:`home.models.home`.

    **Template:**

    :template:`home/home.html`

    """
    aboutInfo = About.objects.all()
    update = Update.objects.all()
    caterer = Caterer.objects.all()
    carousel = Carousel.objects.all()
    context = {
        "about": aboutInfo,
        "updates": update,
        "caterer": caterer,
        "carousel": carousel,
        'all_caterer' : Caterer.objects.all()
    }
    return render(request, "home.html", context)


def rules(request):
    """
    Display the Rules Page :model:`home.models.rules`.

    **Template:**

    :template:`home/rules.html`

    """
    rules = Rule.objects.all()
    shortRebates = ShortRebate.objects.all()
    params = {
        "rule": rules,
        "shortRebate": shortRebates,
    }

    return render(request, "rules.html", params)


def caterer(request, name):
    """
    Display the Caterer Page :model:`home.models.caterer`.

    **Template:**

    :template:`home/caterer.html`

    """
    caterer = Caterer.objects.get(name=name)
    context = {"caterer": caterer}
    return render(request, "caterer.html", context)


def links(request):
    """
    Display the Forms Page :model:`home.models.links`.

    **Template:**

    :template:`home/links.html`

    """
    form = Form.objects.all()
    context = {"form": form}
    return render(request, "links.html", context)


def cafeteria(request):
    """
    Display the Cafeteria Page :model:`home.models.cafeteria`.

    **Template:**

    :template:`home/cafeteria.html`

    """
    cafeteria = Cafeteria.objects.all()
    context = {"cafeteria": cafeteria}
    return render(request, "cafeteria.html", context)


def contact(request):
    """
    Display the Contact Page :model:`home.models.contacts`.

    **Template:**

    :template:`home/contact.html`

    """
    contact = Contact.objects.all()
    context = {"contact": contact}
    return render(request, "contact.html", context)


@login_required
def rebate(request):
    """
    Display the Rebate Form Page :model:`home.models.students`.

    Gets the data from the rebate form checks for the validity of the rebate filled,
    adds the rebte to the rebate model and rebate bills of that semester.
    This form can only be accessed by the Institute community

    **Template:**

    :template:`rebateForm.html`
    """
    text = ""
    list = []
    try:
        print(request.user.email)
        allocation_id = AllocationSpring23.objects.get(roll_no__email=str(request.user.email))
        key = str(allocation_id.student_id)
        # Instead of last use period model to get the allocation id for that period
    except AllocationSpring23.MultipleObjectsReturned:
        try:
            for period in PeriodSpring23.objects.all():
                if period.end_date>date.today()+timedelta(2):
                    period_obj=period
                    break
            allocation_id = AllocationSpring23.objects.get(
                roll_no__email=str(request.user.email),
                month = period_obj
            )
            key = str(allocation_id.student_id) 
        except:
            try:
                allocation_id = AllocationSpring23.objects.filter(
                    roll_no__email=str(request.user.email),
                ).last()
                key = str(allocation_id.student_id)   
            except:
                key="You are not allocated for current period, please contact the dining warden to allocate you to a caterer"
    except AllocationSpring23.DoesNotExist:
        key = "Signed in account does not does not have any allocation ID"     
    if request.method == "POST" and request.user.is_authenticated:
        try:
            start_date = parse_date(request.POST["start_date"])
            end_date = parse_date(request.POST["end_date"])
            diff = ((end_date - start_date).days) + 1
            diff2 = (start_date - date.today()).days
            try:
                student = Student.objects.filter(
                    email=str(request.user.email)
                ).first()
                period = allocation_id.month.Sno
                period_start = allocation_id.month.start_date
                period_end = allocation_id.month.end_date
                ch = check_rebate_spring(allocation_id, student, start_date, end_date, period)
                if not (period_start<=start_date<=period_end and period_start<=end_date<=period_end):
                    text = "Please fill the rebate of this period only"
                elif not is_not_duplicate(student, start_date, end_date,period):
                    text = "You have already applied for rebate for these dates"
                elif ch >= 0:
                    text = (
                        "You can only apply for max 8 days in a period. Days left for this period: "
                        + str(ch)
                    )
                else:
                    if (diff) <= 7 and diff >= 2 and diff2 >= 2:
                        r = Rebate(
                            email=request.user.email,
                            allocation_id=allocation_id,
                            start_date=request.POST["start_date"],
                            end_date=request.POST["end_date"],
                            approved=False,
                        )
                        r.save()
                        text = "You have successfully submitted the form, subject to approval of Office of Dining Warden. Thank You!"
                    elif 0 < diff < 2:
                        text = "Min no of days for rebate is 2"
                    elif diff2 < 2:
                        text = "Form needs to be filled atleast 2 days prior the comencement of leave."
                    elif diff > 7:
                        text = "Max no of days for rebate is 7"
                    elif diff < 0:
                        text = "Please enter the correct dates"
                    else:
                        text = "Your rebate application has been rejected due to non-compliance of the short term rebate rules"
            except AllocationSpring23.DoesNotExist:
                text = "Email ID does not match with the allocation ID"
        except Exception as e:
            print(e)
            text = "Invalid Dates filled"
    context = {"text": text, "key": key, "list": list}
    return render(request, "rebateForm.html", context)

@staff_member_required(redirect_field_name="/", login_url="/")
def allocation(request):
    """
    Display the Rebate Form Page :model:`home.models.students`.

    **Template:**

    :template:`home/allocation.html`

    Gets the data from the allocation csv,
    parses each row and allocates each student an allocation ID and caterer for that month.
    Which can be then exported in the admin page.
    CSV should be imported from /allocation/ url only
    Allocation data should only be filled 2 days prior to the next month
    This form can only be accessed by the Institute's admin
    """
    messages = ""
    if (
        request.method == "POST"
        and request.user.is_authenticated
        and request.user.is_staff
    ):
        try:
            file = request.FILES["csv"]
            file_extension = file.name.split('.')[-1].lower()
            if file_extension == 'csv':
                csv_data = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
            elif file_extension == 'xlsx':
                csv_data = pd.read_excel(file, engine='openpyxl')
            print(csv_data.head())

            for record in csv_data.to_dict(orient="records"):
                try:
                    if 'First Preference' in csv_data.columns:
                        first_pref = str(record["First Preference"]).capitalize()
                    else:
                        first_pref =None
                    if 'Second Preference' in csv_data.columns:
                        second_pref = str(record["Second Preference"]).capitalize()
                    else:
                        second_pref=None
                    if 'Third Preference' in csv_data.columns:
                        third_pref = str(record["Third Preference"]).capitalize()
                    else:
                        third_pref=None
                    if 'Period' in csv_data.columns:
                        period = str(record["Period"]).capitalize()
                        period_obj = PeriodSpring23.objects.get(Sno=period)
                    else:
                        period_obj = PeriodSpring23.objects.filter().last()
                    high_tea = record["High Tea"]
                    if(high_tea=="Yes" or high_tea=="True"):
                        high_tea=True
                    else:
                        high_tea=False
                    student = Student.objects.filter(email=record["Email"]).first()
                    print(student)
                    for pref in [first_pref, second_pref, third_pref]:
                        kanaka = Caterer.objects.get(name="Kanaka")
                        ajay = Caterer.objects.get(name="Ajay")
                        gauri = Caterer.objects.get(name="Gauri")
                        if pref == kanaka.name and kanaka.student_limit > 0:
                            student_id = str(kanaka.name[0])
                            if high_tea == True:
                                student_id += "H"
                            student_id += str(kanaka.student_limit)
                            caterer_name = kanaka.name
                            kanaka.student_limit -= 1
                            kanaka.save(update_fields=["student_limit"])
                            break
                        elif pref == ajay.name and ajay.student_limit > 0:
                            student_id = str(ajay.name[0])
                            if high_tea == True:
                                student_id += "H"
                            student_id += str(ajay.student_limit)
                            caterer_name = ajay.name
                            ajay.student_limit -= 1
                            ajay.save(update_fields=["student_limit"])
                            break
                        elif pref == gauri.name and gauri.student_limit > 0:
                            student_id = str(gauri.name[0])
                            if high_tea == True:
                                student_id += "H"
                            student_id += str(gauri.student_limit)
                            caterer_name = gauri.name
                            gauri.student_limit -= 1
                            gauri.save(update_fields=["student_limit"])
                            break
                    a = AllocationSpring23(
                        roll_no=student,
                        student_id=student_id,
                        month=period_obj,
                        caterer_name=caterer_name,
                        high_tea=high_tea,
                        first_pref=first_pref,
                        second_pref=second_pref,
                        third_pref=third_pref,
                    )
                    a.save()
                    UnregisteredStudent.objects.filter(email=student.email).delete()
                except Exception as e:
                    print(e)
            messages = "Form submitted. Please check the admin page."
        except Exception as e:
            print(e)
            messages = "Invalid CSV file"
    period_obj = PeriodSpring23.objects.get(Sno=5)
    Ajay_high_tea = AllocationSpring23.objects.filter(caterer_name="Ajay", high_tea=True,month=period_obj).count()
    Gauri_high_tea = AllocationSpring23.objects.filter(caterer_name="Gauri", high_tea=True,month=period_obj).count()
    Kanaka_high_tea = AllocationSpring23.objects.filter(caterer_name="Kanaka", high_tea=True,month=period_obj).count()
    Ajay_total = AllocationSpring23.objects.filter(caterer_name="Ajay",month=period_obj).count()
    Gauri_total = AllocationSpring23.objects.filter(caterer_name="Gauri",month=period_obj).count()
    Kanaka_total = AllocationSpring23.objects.filter(caterer_name="Kanaka",month=period_obj).count()
    Ajay_left = Caterer.objects.get(name="Ajay").student_limit
    Gauri_left = Caterer.objects.get(name="Gauri").student_limit
    Kanaka_left = Caterer.objects.get(name="Kanaka").student_limit
    caterer_list = [["Ajay",Ajay_high_tea,Ajay_total,Ajay_left], ["Gauri",Gauri_high_tea,Gauri_total,Gauri_left], ["Kanaka", Kanaka_high_tea,Kanaka_total,Kanaka_left]]
    context = {"messages": messages,"list": caterer_list}
    return render(request, "admin/allocation.html", context)

@login_required
def addLongRebateBill(request):
    """
    Display the Rebate Form Page :model:`home.models.students`.

    **Template:**

    :template:`home/longRebate.html`

    Gets the data from the log term rebate form , and adds it to the coresponding rebate bill
    This form can only be accessed by the Institute's admin
    """
    text = ""
    try:
        allocation_id = AllocationSpring23.objects.get(roll_no__email=str(request.user.email))
        key = str(allocation_id.student_id)
    except AllocationSpring23.DoesNotExist:
        key = "Signed in account does not does not have any allocation ID"
    # Instead of last use period model to get the allocation id for that period
    except AllocationSpring23.MultipleObjectsReturned:
        allocation_id = AllocationSpring23.objects.filter(
            roll_no__email=str(request.user.email)
        ).last()
        key = str(allocation_id.student_id)
    if request.method == "POST" and request.user.is_authenticated:
        try:
            start_date = parse_date(request.POST["start_date"])
            end_date = parse_date(request.POST["end_date"])
            days = (end_date - start_date).days + 1
            student = Student.objects.get(email=request.user.email)
            if not is_not_duplicate(student, start_date, end_date,0):
                text = "You have already applied for rebate for these dates"
            else:
                try:
                    file=request.FILES["pdf"]
                    print(file)
                    long = LongRebate(
                        email=student,
                        start_date=start_date,
                        end_date=end_date,
                        days=days,
                        approved=False,
                        file=file,
                    )
                    long.save()
                    text = "Long Term rebate added Successfully"
                except Exception as e:
                    text = "Allocation ID for the entered email does not exist"
                    print(e)
        except:
            text = "Email ID does not exist in the database. Please eneter the correct email ID"
    context = {"text": text, "key": key}
    return render(request, "longRebate.html", context)

@login_required
def profile(request):
    """
    Display the Profile Page :model:`home.models.students`.

    **Template:**

    :template:`home/profile.html`

    Gets the data from the profile form , and updates the student's profile
    This form can only be accessed by the Institute's admin
    """
    text = ""
    student = Student.objects.filter(email=str(request.user.email)).last()
    socialaccount_obj = SocialAccount.objects.filter(provider='google', user_id=request.user.id)
    picture = "not available"
    if len(socialaccount_obj):
            picture = socialaccount_obj[0].extra_data['picture']
    if request.method == "POST" and request.user.is_authenticated:
        try:
            student = Student.objects.get(email=str(request.user.email))
            student.name = request.POST["name"]
            student.room_no = request.POST["room_no"]
            student.save()
            text = "Profile Updated Successfully"
        except:
            text = "Email ID does not exist in the database. Please eneter the correct email ID"
    context = {"text": text,"student":student,"picture":picture}
    return render(request, "profile.html", context)

@login_required
def period_data(request):
    print("period_data")
    semester = request.GET.get('semester')
    if(semester=="autumn22"):
        period = PeriodAutumn22.objects.all()
    elif(semester=="spring23"):
        period = PeriodSpring23.objects.all()
    elif(semester=="autumn23"):
        period = PeriodAutumn23.objects.all()
    period_data = {
        'semester': semester,
        'data': list(period.values('start_date', 'end_date')),
    }
    # print(period_data['semester'])
    # print(period_data['data'])
    return JsonResponse(period_data)

@login_required
def rebate_data(request):
    print("rebate_data")
    user = request.user
    student = Student.objects.get(email=user.email)
    sno = request.GET.get('period')
    semester = request.GET.get('semester')
    if(semester=="autumn22"):
        rebate = RebateAutumn22.objects.filter(email=student).last()
        rebate_bills = get_rebate_bills(rebate,sno)
    elif(semester=="spring23"):
        rebate = RebateSpring23.objects.filter(email=student).last()
        print(rebate)
        rebate_bills = get_rebate_bills(rebate,sno)
    elif(semester=="autumn23"):
        rebate = RebateAutumn23.objects.filter(email=student).last()
        rebate_bills = get_rebate_bills(rebate,sno)
    rebate_data = {
        'semester': semester,
        'period': sno,
        'data':rebate_bills
    }
    return JsonResponse(rebate_data)