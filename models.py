from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_admin')
    registration_id=models.CharField(max_length =100,null=True,blank =True,unique=True)
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Branch(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='branch_admin')
    registration_id=models.CharField(max_length =100,null=True,blank =True,unique=True)
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company,on_delete=models.SET_NULL,null=True,blank=True,related_name='company_branches')
    address = models.TextField()
    location = models.CharField(max_length=100,null=True,blank=True)
    contact_number=models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else "No Company"}"
    

class Department(models.Model):
    name = models.CharField(max_length=100)
    branch = models.ForeignKey('Branch', on_delete=models.SET_NULL,null=True, blank=True, related_name='branch_departments')
    # company=models.ForeignKey('Company',on_delete=models.SET_NULL,null=True, blank=True,related_name='company_departments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_custom = models.BooleanField(default=False)   
    #globally created department is set false and for custom department this is set true
    
    class Meta:
        unique_together = ('name', 'branch')

    def __str__(self):
        return f"{self.name}"

class Canteen(models.Model):
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_canteens')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    
class CanteenProfile(models.Model):
    name=models.CharField(max_length=100)
    canteen=models.ManyToManyField(Canteen,related_name='canteen_profiles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# class EmployeeType(models.Model): 
#     class Employee_Types(models.TextChoices):
#         INTERN = 'intern','Intern'
#         TRAINEE ='trainee','Trainee'
#         DEVELOPER ='developer','Developer'
#         HOD = 'hod','Deartment Head'
    
#     employee_type=models.CharField(choices=Employee_Types.choices,max_length=12)


class Employee(models.Model):
    class EmployeeType(models.TextChoices):
        INTERN = 'intern','Intern'
        TRAINEE ='trainee','Trainee'
        DEVELOPER ='developer','Developer'
        HOD = 'hod','Deartment Head'
    
    biometric_id=models.IntegerField(unique=True)
    employee_id = models.CharField(max_length=20, blank=True, null=True, unique=True)
    name = models.CharField(max_length=100)
    branch = models.ForeignKey(Branch,on_delete=models.SET_NULL,null=True,blank=True,related_name='branch_employees')
    department = models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True,related_name='department_employees')
    designation = models.CharField(max_length=100, blank=True, null=True)
    employee_type=models.CharField(choices=EmployeeType.choices,default="developer",max_length=12)
    # employee_type = models.ForeignKey(EmployeeType, on_delete=models.SET_NULL, null=True, blank=True,related_name='employee_type')
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    canteen=models.ForeignKey(Canteen,on_delete=models.SET_NULL,null=True,blank=True,related_name='employee_canteens')
    canteen_profile=models.ForeignKey(CanteenProfile,on_delete=models.SET_NULL,null=True,blank=True,related_name='employee_canteen_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"
    
    class Meta:
        indexes = [
            models.Index(fields=['biometric_id']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['branch', 'is_active']),
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    

class Device(models.Model):
    serial_number = models.CharField(max_length=100, unique=True)
    canteen = models.ForeignKey(Canteen, on_delete=models.SET_NULL,null=True,blank=True, related_name='canteen_devices')
    company=models.ForeignKey(Company, on_delete=models.SET_NULL,null=True,blank=True, related_name='company_devices')

    def __str__(self):
        return self.serial_number


class Printer(models.Model):
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='device_printers')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.serial_number


class MealLog(models.Model):
    class MEALTYPE (models.TextChoices):
       BREAKFAST =  'breakfast', 'Breakfast'
       LUNCH =  'lunch', 'Lunch'
       SNACKS =  'snacks', 'Snacks'
       DINNER =  'dinner', 'Dinner'
       SPECIAL = 'special', 'Special Meal'        

    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='employee_meal_logs')
    device = models.ForeignKey('Device', on_delete=models.SET_NULL, null=True, blank=True,related_name='device_logs')
    meal_type = models.CharField(max_length=20, choices=MEALTYPE.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['employee', 'meal_type', 'created_at']),
            models.Index(fields=['device', 'created_at']),
        ]

    def __str__(self):
        return f"{self.employee} - {self.meal_type} token generated @ {self.created_at}"