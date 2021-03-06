from django.contrib.auth.models import AnonymousUser
from django.http import request
from django.shortcuts import render,redirect
from django.http.response import JsonResponse
from .forms import Registrationform
from .models import Accounts
from django.contrib import messages,auth
from productmanagement.models import Products
from cart.models import Order, OrderItems
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
from cart.models import UserAddress
from django.views.decorators.cache import never_cache
from cart.models import CartItems
import uuid
from django.conf import settings
from twilio.rest import Client





def _session_id(request):
    session_id = request.session.session_key
    if not request.session.session_key:
        session_id = request.session.create()

        print(request.session.session_key)
    return session_id


# Create your views here.
@never_cache
def login(request):

    if request.session.has_key('userlogin'):
        product = Products.objects.all()


        return render(request,'user/home.html', {'products': product})

    else: 
        if request.method == 'POST':
            username = request.POST['username']
            password = request.POST['password']

            user = auth.authenticate(username = username, password = password)
            product = Products.objects.all()
        

            if user is not None:
                request.session['userlogin'] = True
                
                auth.login(request, user)

                one = str(uuid.uuid4())
                return redirect('home')   


            else:
                messages.info(request, 'Invalid credential')
                return redirect('login')

        else:

            return render(request,'user/login.html')

@never_cache
def register(request):
    if request.method == 'POST':
        form = Registrationform(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            referral_code = str(uuid.uuid4())[0:8]
            user = Accounts.objects.create_user(first_name = first_name, last_name = last_name, username = username, email = email, password = password)
            user.referral_code = referral_code
            user.phone_number = phone_number
            user.save()

            # Checking if the referral order
            if form.cleaned_data['referral_code']:

                entered_referral_code = form.cleaned_data['referral_code']
                print(entered_referral_code)

                if Accounts.objects.get(referral_code = entered_referral_code):
                    referred_user = Accounts.objects.get(referral_code = entered_referral_code)
                    referred_user.wallet_amount += 10
                    user.wallet_amount +=10
                    referred_user.save()
                    user.save()
                else:
                    pass
                                        
                    
            else:
                pass



            messages.success(request,'Registration Successful')
            return redirect('register')

        else:
            messages.info(request,'Registration Not Successful')
            return redirect('register')



    else:

        form = Registrationform()
    context = {
        'form':form
    }
    return render(request, 'user/register.html',context)


@never_cache
def logout(request):
    if request.session.has_key('userlogin'):
        del request.session['userlogin']
        auth.logout(request)
    return redirect('login')

# Phone number (OTP) 


def otp_login(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        user = Accounts.objects.get(phone_number= phone_number)

        request.session['phone_number'] = phone_number

        return redirect('verify_otp')


    else:

        return render(request, 'user/otp_login.html')


# OTP Verify

def verify_otp(request):
    if request.method == "POST":
        # generated_otp = request.POST['generated_otp']
        otp_input = request.POST.get('otp_input')
        user_mobile = request.session['phone_number']
        org_user_mobile = '+91'+ user_mobile
        user_email = request.session['user_email']        
        account_sid = settings.ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN

        TWILIO_SERVICE_SID = settings.TWILIO_SERVICE_SID
        client = Client(account_sid, auth_token)

        verification_check = client.verify \
                                .services(TWILIO_SERVICE_SID) \
                                .verification_checks \
                                .create(to= org_user_mobile, code= otp_input)
    
        print(verification_check.status)

        if verification_check.status == "approved":
            user = Accounts.objects.get(email=user_email) 

            auth.login(request,user)   
            request.session['userlogin'] = True     
            try:
                del request.session['phone_number']
                del request.session['user_email']
            except:
                pass              
            
            # print('signing in')
            return redirect('home')
        else:
            messages.info(request,"Invalid OTP. Try again with correct OTP")
            return redirect(request.META.get('HTTP_REFERER', 'otp_login'))
    else:

        # print('request to generate OTP')
        phone_number = request.session['phone_number']
        # print(user_email)
        
        
        user = Accounts.objects.get(phone_number=phone_number)

        mobile = user.phone_number
        email = user.email
        
        
        user_mobile = '+91'+ mobile
        print(user_mobile)
        request.session['user_email'] = email
        
        auth_sid = settings.ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        
        client = Client(auth_sid,auth_token)
        
        verification = client.verify \
                     .services(settings.TWILIO_SERVICE_SID) \
                     .verifications \
                     .create(to= user_mobile, channel='sms')
        
        return render(request,'user/otp_enter.html')




def my_account(request):
    user    = request.user.id
    current_user  = Accounts.objects.get(id = user)

    orders = Order.objects.filter(user = current_user).order_by('-id')

    sub_orders = OrderItems.objects.all()

    products = Products.objects.all()

    user_addresses = UserAddress.objects.filter(user = current_user)


    

    context = {
        'current_user' : current_user,
        'orders' : orders,
        'sub_orders' : sub_orders,
        'products' : products,
        'user_addresses' : user_addresses


    }
    return render(request, 'user/my_account.html', context)



def my_account_orders(request):
    user    = request.user.id
    orders  = Order.objects.filter(user_id = user)
    for orr in orders:

        print(orr.order_id)

    context = {
        'orders' : orders
    }
    return render(request, 'user/my_account.html', context)


# change account details
@never_cache
def change_account_details(request):
    id = request.user.id
    current_user = Accounts.objects.get(id = id)

    
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone_number = request.POST['phone_number']
        email = request.POST['email']
        username = request.POST['username']
        if first_name is not None:
            current_user.first_name = first_name
        
        if last_name is not None:
            current_user.last_name = last_name

        if phone_number is not None:
            current_user.phone_number = phone_number

        if Accounts.objects.filter(username = username).exists():
            messages.info(request,'Username Exist')
            return redirect('my_account')  
         

        if email is not None:
            current_user.email = email

        if phone_number is not None:
            current_user.phone_number = phone_number

        current_user.save()

        messages.success(request,'Details Changed')
        return redirect('my_account')
    else:
        return redirect('my_account')

# change password

@never_cache
def change_password(request):
    if request.method == 'POST':
        old_password = request.POST['old_password']
        new_password = request.POST['new_password']
        repeat_password = request.POST['repeat_password']
        if old_password and new_password and new_password == repeat_password:
            current_user = Accounts.objects.get(id=request.user.id)

            if current_user.check_password(old_password):
                current_user.set_password(new_password)
                current_user.save()
                update_session_auth_hash(request,current_user)
                messages.info(request,'Password Successfully Changed')
                return redirect('my_account')
            else:
                messages.info(request,'Old Password incorrect')
                return redirect('my_account')
        else:
            messages.info(request,'Password Mismatch')
            return redirect('my_account')


# my orders

def my_orders(request):
    current_user_id = request.user.id
    current_user = Accounts.objects.get(id = current_user_id)

    orders = Order.objects.filter(user = current_user).order_by('-id')

    sub_orders = OrderItems.objects.all()

    products = Products.objects.all()


    context = {
        'orders' : orders,
        'sub_orders' : sub_orders,
        'products' : products
    }
    return render(request, 'user/my_account_orders.html', context)


# cancel order

@csrf_exempt
def cancel_order(request):
    order_id = request.POST['order_id']
    order = Order.objects.get(id = order_id)
    order.delivery_status = 'cancelled'
    order.save()
    return JsonResponse('',safe=False)

# user address display


def my_address(request):
    user_id = request.user.id
    current_user = Accounts.objects.get(id = user_id)
    user_addresses = UserAddress.objects.filter(user = current_user)

    context = {
        'user_addresses' : user_addresses
    }

    return render(request, 'user/my_account_address.html', context)

#change user address
@never_cache
def my_account_address_edit(request, id):
    current_user_address = UserAddress.objects.get(id = id)
    if request.method == 'POST':
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        phone_number = request.POST['phone_number']
        email = request.POST['email']
        address = request.POST['address']
        country = request.POST['country']
        city = request.POST['city']
        post_code = request.POST['post_code']
        state = request.POST['state']


        if first_name is not None:
            current_user_address.first_name = first_name
        
        if last_name is not None:
            current_user_address.last_name = last_name

        if phone_number is not None:
            current_user_address.phone_number = phone_number 
        

        if email is not None:
            current_user_address.email = email
        
        if address is not None:
            current_user_address.address = address

        if country is not None:
            current_user_address.country = country

        if city is not None:
            current_user_address.city = city

        if post_code is not None:
            current_user_address.post_code = post_code

        if state is not None:
            current_user_address.state = state

        
        current_user_address.save()

        messages.success(request,'Address Succesfully Changed')
        return redirect('my_address')

    
    else:

        address = UserAddress.objects.get(id = id)
        context = {
            'address' : address
        }
        return render(request, 'user/my_account_address_edit.html', context)


# delete address

@csrf_exempt
def delete_address(request):
    address_id = request.POST['address_id']
    UserAddress.objects.get(id = address_id).delete()
    return JsonResponse('',safe=False)





        

