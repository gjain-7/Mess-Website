from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Student, Rebate, LongRebate, TodayRebate, AllocationSpring23,PeriodAutumn23,PeriodSpring23, RebateAutumn23, RebateSpring23, UnregisteredStudent
from .utils.rebate_checker import count, is_present_autumn, is_present_spring
from .utils.django_email_server import rebate_mail,long_rebate_mail
from .utils.month import fill_periods
from .utils.rebate_bills_saver import save_short_bill, save_long_bill

__doc__="This file contains the signals for the home app"

@receiver(post_save, sender=Student)
def create_bill(sender, instance, created, **kwargs):
    if created:
        rebate_autumn_sem, _ =RebateAutumn23.objects.get_or_create(email=instance)
        rebate_spring_sem, _ =RebateSpring23.objects.get_or_create(email=instance)
        rebate_autumn_sem.save()
        rebate_spring_sem.save()


@receiver(pre_save, sender=Rebate)
def update_short_bill(sender, instance, **kwargs):
    print("Signal called for Short Rebate")
    try:
        old_instance = Rebate.objects.get(pk=instance.pk)
        if old_instance.approved != instance.approved:
            days = count(instance.start_date, instance.end_date)
            email = instance.email
            allocation = instance.allocation_id
            print(old_instance.approved,instance.approved)
            if instance.approved == True:
                save_short_bill(email,allocation.month,days,allocation.high_tea, allocation.caterer_name)
                new_rebate = TodayRebate(date=instance.date_applied,Caterer=allocation.caterer_name,allocation_id = allocation,start_date=instance.start_date,end_date=instance.end_date)
                new_rebate.save()
                print("Saved")
            else:
                save_short_bill(email,allocation.month,-days,allocation.high_tea, allocation.caterer_name)
                new_rebate = TodayRebate.objects.filter(allocation_id=allocation).last().delete()
                print("Deleted")
            rebate_mail(instance.start_date,instance.end_date,instance.approved,email)
    except Exception as e:
        print(e)


@receiver(pre_save, sender=LongRebate)
def update_long_bill(sender, instance, **kwargs):
    print("Signals called for long rebate")
    try:
        old_instance = LongRebate.objects.get(pk=instance.pk)
        print("inside try")
        print(old_instance.approved,instance.approved)
        if old_instance.approved != instance.approved:
            email = instance.email
            days_per_period = fill_periods(email,instance.start_date, instance.end_date)
            left_start_date,left_end_date = [days for period,days in days_per_period if period==7 or period==8]
            if instance.approved == True:
                save_long_bill(email,days_per_period,1)
                long_rebate_mail(instance.start_date,instance.end_date,instance.approved,email.email,left_start_date,left_end_date)
            else:
                save_long_bill(email,days_per_period,-1)
                long_rebate_mail(instance.start_date,instance.end_date,instance.approved,email.email,left_start_date,left_end_date)
    except Exception as e:
        print(e)

@receiver(post_save, sender=AllocationSpring23)
def update_spring_bill(sender, instance, created, **kwargs):
    try:
        if created:
            sno = instance.month.Sno
            days = (instance.month.end_date - instance.month.start_date).days + 1
            high_tea = instance.high_tea
            rebate_bill = is_present_spring(instance.roll_no)
            amount=115
            if(high_tea):
                amount=130
            if sno == 1:
                rebate_bill.period1_high_tea = high_tea
                rebate_bill.period1_bill = amount*days
            elif sno == 2:
                rebate_bill.period2_high_tea = high_tea
                rebate_bill.period2_bill = amount*days
            elif sno == 3:
                rebate_bill.period3_high_tea = high_tea
                rebate_bill.period3_bill = amount*days
            elif sno == 4:
                rebate_bill.period4_high_tea = high_tea
                rebate_bill.period4_bill = amount*days
            elif sno == 5:
                rebate_bill.period5_high_tea = high_tea
                rebate_bill.period5_bill = amount*days
            elif sno == 6:
                rebate_bill.period6_high_tea = high_tea
                rebate_bill.period6_bill = amount*days
            rebate_bill.save()
    except Exception as e:
        print(e)

@receiver(post_save, sender=PeriodSpring23)
def create_unregistered(sender, instance,created, **kwargs):
    if created:
        for student in Student.objects.all():
            unregistered,_ = UnregisteredStudent.objects.get_or_create(email=str(student.email))
            unregistered.period = instance
            unregistered.save()