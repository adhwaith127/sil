from django.contrib.auth.models import User
from django.db import models

class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    registration_id=models.CharField(max_length =100,null=True,blank =True)
    contact_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='branch_profile')
    company = models.ForeignKey(Company,on_delete=models.SET_NULL,null=True,blank=True,related_name='branches')
    name = models.CharField(max_length=100)
    address = models.TextField()
    registration_id=models.CharField(max_length =100,null=True,blank =True)
    location = models.CharField(max_length=100,null=True,blank=True)
    contact_number=models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name}"

    
class Department(models.Model):
    name = models.CharField(max_length=100)
    company=models.ForeignKey('Company',on_delete=models.SET_NULL,null=True, blank=True,related_name='departments')
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL,null=True, blank=True, related_name='departments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_custom = models.BooleanField(default=False)   #global department is false and for custom department this can be set true
    
    class Meta:
    unique_together = ('name', 'branch')


class EmployeeType(models.Model):
    
    EMPLOYEE_TYPES = [('',''),('',''),('','')]
    
    employee_type=models.CharField(choices=EMPLOYEE_TYPES)
    


class Employee(models.Model):

    #EMPLOYEE_TYPES = [('',''),('',''),('','')]	
	
    employee_id = models.CharField(max_length=20, blank=True, null=True)
    biometric_id=models.IntegerField()
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch,on_delete=models.SET_NULL,null=True,blank=True,related_name='branch_emp')
    department = models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True,related_name='departments_emp')
    designation = models.CharField(max_length=100, blank=True, null=True)
    #employee_type=models.CharField(choices=EMPLOYEE_TYPES)
    employee_type = models.ForeignKey(EmployeeType, on_delete=models.SET_NULL, null=True, blank=True,related_name='emp_type')
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    canteen=models.ForeignKey(Canteen,on_delete=models.SET_NULL,null=True,blank=True,related_name='emp_canteens')
    canteen_profile=models.ForeignKey(CanteenProfile,on_delete=models.SET_NULL,null=True,blank=True,related_name='emp_canteen_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


class Printer(models.Model):
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='printers')
    is_active = models.BooleanField(default=True)
    
    

class Device(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    canteen = models.ForeignKey(Canteen, on_delete=models.SET_NULL,null=True,blank=True, related_name='canteen_devices')
    company=models.ForeignKey(Company, on_delete=models.SET_NULL,null=True,blank=True, related_name='company_devices')

    
class CanteenProfile(models.Model):
    name=models.CharField(max_length=100)
    canteens=models.ManyToManyField(Canteen,related_name='profiles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Canteen(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_canteens')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    #canteen_profile=models.ForeignKey(CanteenProfile, on_delete=models.SET_NULL,null=True,blank=True, related_name='canteens')



class MealLog(models.Model):
    
    MEAL_TYPES = [
       ('breakfast', 'Breakfast'),('lunch', 'Lunch'),('snacks', 'Snacks'),('dinner', 'Dinner'),('special', 'Special Meal')]

    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='meal_logs_employee')
    device = models.ForeignKey('Device', on_delete=models.SET_NULL, null=True, blank=True)
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)  




    
    
# class UserProfile(models.Model):
#     ROLE_CHOICES = (
#         ('employee', 'Employee'),
#         ('canteen', 'Canteen User'),
#     )

#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
#     branch = models.ForeignKey(Branch, related_name='user_profiles')
#     role = models.CharField(max_length=20, choices=ROLE_CHOICES)
#     employee_id = models.CharField(max_length=20, blank=True, null=True)
#     canteen_name = models.CharField(max_length=100)

#     def __str__(self):
#         return f"{self.user.username} ({self.role})"
