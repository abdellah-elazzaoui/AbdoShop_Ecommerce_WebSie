from django.shortcuts import render
from rest_framework.decorators import api_view,permission_classes
from .models import Product,Cart,CartItem,Transaction
from .serializer import ProductSerializer,DetaileProductSerializer,CartItemSerializer,SimpleCartSerializer,CartSerializer,UserSerializer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import uuid
from decimal import Decimal
from django.conf import settings
import requests
from django.contrib.auth import get_user_model
import paypalrestsdk
import os

# BASE_URL = "http://localhost:3000"

BASE_URL = settings.REACT_BASE_URL

# Create your views here.

@api_view(['GET'])
def products(request):
    products=Product.objects.all()
    serializer = ProductSerializer(products,many=True)
    return Response(serializer.data)

@api_view(['GET'])
def product_detail(request, slug):
    try:
        # Use get_object_or_404 for better error handling
        product = get_object_or_404(Product, slug=slug)
        serializer = DetaileProductSerializer(product)
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)


@api_view(['POST'])
def add_item(request):
    try: 
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")
        cart, cart_created = Cart.objects.get_or_create(cart_code=cart_code)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

        cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product)

        if item_created:
            cart_item.quantity = 1
        else:
            cart_item.quantity += 1
            
        cart_item.save()

        serializer = CartItemSerializer(cart_item)

        return Response({
            "data": serializer.data, 
            "message": "Item added to cart successfully"
        }, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    cart = Cart.objects.get(cart_code=cart_code)
    product = Product.objects.get(id=product_id)
    
    
    product_exist_in_cart = CartItem.objects.filter(cart=cart,product=product).exists()

    return Response({'product_in_cart':product_exist_in_cart})

@api_view(['GET'])
def get_cart_stat(request):
    try:
        cart_code = request.query_params.get("cart_code")
        if not cart_code:
            return Response({"error": "cart_code is required"}, status=400)
        cart = Cart.objects.get(cart_code=cart_code, paid=False)
        serializer = SimpleCartSerializer(cart)
        return Response(serializer.data)
    except Cart.DoesNotExist:
        return Response({
            "id": None,
            "cart_code": cart_code,
            "num_of_items": 0,
            "message": "Cart not found"
        }, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_cart(request):
    cart_code = request.query_params.get("cart_code")
    cart =Cart.objects.get(cart_code=cart_code,paid=False)
    serializer = CartSerializer(cart)
    return Response(serializer.data)


@api_view(['PATCH'])
def update_quantity(request):
    try:
        cartitem_id = request.data.get('item_id')
        quantity = int(request.data.get('quantity'))
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer = CartItemSerializer(cartitem)
        return Response({"data":serializer.data,"message":'CartItem updated Sucssefully!'})
    except Exception as e:
        return Response({'error':str(e)},status=400)

@api_view(['POST'])
def delete_cartitem(request):
    cartitem_id = request.data.get("item_id")
    cartitem = CartItem.objects.get(id=cartitem_id)
    cartitem.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    return Response({"username":user.username})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)



User = get_user_model()

@api_view(['POST'])
def register_user(request):
    try:
        data = request.data
        required_fields = ['username', 'email', 'password', 'confirm_password']
        
        for field in required_fields:
            if field not in data:
                return Response(
                    {'error': f"{field} is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Check if passwords match
        if data['password'] != data['confirm_password']:
            return Response(
                {'error': "Passwords do not match"},  
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=data['username']).exists():
            return Response(
                {"error": f"Username '{data['username']}' already exists, please try another one"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=data['email']).exists():
            return Response(
                {"error": "Email already exists, please try another one"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', '')
        )
        
        serializer = UserSerializer(user)
        return Response({
            'message': 'User registered successfully',
            'user': serializer.data,
        }, status=status.HTTP_201_CREATED)  

    except Exception as e:
        return Response({
            'error': f"Registration failed: {str(e)}", 
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)







@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_payment(request):
    if request.user:
        try:
            
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            user = request.user
            cart = Cart.objects.get(cart_code=cart_code)
            amount = sum([item.quantity * item.product.price for item in cart.items.all()])
            tax = Decimal("4")
            total_amount = amount + tax
            currency = "NGN"
            redirect_url = f"{BASE_URL}/payment-page"

            transaction = Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency=currency,
                user=user,
                status='pending'
            )

            flutterwave_payload = {
                "tx_ref": tx_ref,
                "amount": str(total_amount),
                "currency": currency,
                "redirect_url": redirect_url,
                "customer": {
                    "email": user.email,
                    "name": user.username,
                    "phonenumber": user.phone,  # Fixed typo: phonenmber -> phonenumber
                },
                "customization": {
                    "title": "AbdoShop Payment"
                }
            }

            headers = {
                "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",  # Fixed typo: Authorizatoin -> Authorization
                "Content-Type": "application/json"  # Fixed typo: content-Type -> Content-Type
            }

            response = requests.post(
                "https://api.flutterwave.com/v3/payments",  # Fixed missing colon after https
                json=flutterwave_payload,
                headers=headers
            )

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
        except requests.exceptions.RequestException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Allow unauthenticated callbacks from Flutterwave
def payment_callback(request):
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')

    # Validate required parameters
    if not all([status, tx_ref, transaction_id]):
        return Response({
            "message": "Missing Parameters",
            "SubMessage": "Required payment information is missing"
        }, status=400)

    if status == "successful":
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}" 
        }

        try:
            response = requests.get(
                f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",  
                headers=headers
            )
            response_data = response.json()

            if response_data['status'] == "success":  
                transaction = Transaction.objects.get(ref=tx_ref)

                if (
                    response_data['data']['status'] == "successful" and  
                    float(response_data['data']['amount']) == float(transaction.amount) and 
                    response_data['data']['currency'] == transaction.currency
                ):
                    transaction.status = "completed"
                    transaction.save()

                    cart = transaction.cart
                    cart.paid = True
                    if request.user.is_authenticated:
                        cart.user = request.user
                    cart.save()

                    return Response({
                        "message": "Payment Successful",  
                        "SubMessage": "You have successfully made payment"  
                    })
                
                else:
                    return Response({  
                        "message": "Payment Verification Failed", 
                        "SubMessage": "Payment details do not match"
                    }, status=400)
            else:
                return Response({
                    "message": "Failed to verify your transaction with Flutterwave",  
                    "SubMessage": "Something went wrong, please try again"  
                }, status=400)
        
        except Transaction.DoesNotExist:
            return Response({
                "message": "Transaction Not Found",
                "SubMessage": "The transaction reference is invalid"
            }, status=404)
        except Exception as e:
            return Response({
                "message": "Verification Error",
                "SubMessage": str(e)
            }, status=500)
    else:
        return Response({
            "message": "Payment was not successful",
            "SubMessage": "Your payment was cancelled or failed"
        }, status=400)
    
 





# Configure PayPal
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_paypal_payment(request):
    if request.user:
        try:
            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            user = request.user
            cart = Cart.objects.get(cart_code=cart_code)
            
            amount = sum([item.quantity * item.product.price for item in cart.items.all()])
            tax = Decimal("4")
            total_amount = amount + tax
            
            # Create transaction record
            transaction = Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency="USD",  # PayPal typically uses USD, change if needed
                user=user,
                status='pending'
            )
            
            # Create PayPal payment
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": f"{BASE_URL}/paypal-callback?tx_ref={tx_ref}",
                    "cancel_url": f"{BASE_URL}/payment-page?status=cancelled&tx_ref={tx_ref}"
                },
                "transactions": [{
                    "item_list": {
                        "items": [
                            {
                                "name": f"Order {cart_code}",
                                "sku": cart_code,
                                "price": str(float(amount)),
                                "currency": "USD",
                                "quantity": 1
                            },
                            {
                                "name": "Tax",
                                "sku": "TAX",
                                "price": str(float(tax)),
                                "currency": "USD",
                                "quantity": 1
                            }
                        ]
                    },
                    "amount": {
                        "total": str(float(total_amount)),
                        "currency": "USD"
                    },
                    "description": f"Payment for AbdoShop Order {cart_code}",
                    "custom": tx_ref  # Store transaction reference
                }]
            })
            
            if payment.create():
                # Find approval URL
                approval_url = None
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = link.href
                        break
                
                if approval_url:
                    return Response({
                        "status": "success",
                        "data": {
                            "link": approval_url,
                            "payment_id": payment.id,
                            "tx_ref": tx_ref
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'error': 'Approval URL not found'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({
                    'error': payment.error
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Cart.DoesNotExist:
            return Response({
                'error': 'Cart not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({
        'error': 'User not authenticated'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])  # Allow unauthenticated callbacks from PayPal
def paypal_callback(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    tx_ref = request.GET.get('tx_ref')
    
    # Validate required parameters
    if not all([payment_id, payer_id, tx_ref]):
        return Response({
            "message": "Missing Parameters",
            "SubMessage": "Required payment information is missing"
        }, status=400)
    
    try:
        # Get the transaction from database
        transaction = Transaction.objects.get(ref=tx_ref)
        
        # Get PayPal payment details
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment:
            # Execute the payment
            if payment.execute({"payer_id": payer_id}):
                # Payment successful - verify amount and currency
                paypal_amount = float(payment.transactions[0].amount.total)
                paypal_currency = payment.transactions[0].amount.currency
                
                if (
                    payment.state == "approved" and
                    abs(paypal_amount - float(transaction.amount)) < 0.01 and  # Allow small rounding differences
                    paypal_currency == transaction.currency
                ):
                    # Update transaction status
                    transaction.status = "completed"
                    transaction.save()
                    
                    # Update cart
                    cart = transaction.cart
                    cart.paid = True
                    if request.user.is_authenticated:
                        cart.user = request.user
                    cart.save()
                    
                    return Response({
                        "message": "Payment Successful",
                        "SubMessage": "You have successfully made payment via PayPal"
                    })
                else:
                    return Response({
                        "message": "Payment Verification Failed",
                        "SubMessage": "Payment details do not match"
                    }, status=400)
            else:
                # Payment execution failed
                return Response({
                    "message": "Payment Execution Failed",
                    "SubMessage": payment.error.get('message', 'Unable to complete payment')
                }, status=400)
        else:
            return Response({
                "message": "Payment Not Found",
                "SubMessage": "Unable to find payment details"
            }, status=404)
            
    except Transaction.DoesNotExist:
        return Response({
            "message": "Transaction Not Found",
            "SubMessage": "The transaction reference is invalid"
        }, status=404)
    except paypalrestsdk.ResourceNotFound:
        return Response({
            "message": "PayPal Payment Not Found",
            "SubMessage": "Unable to verify payment with PayPal"
        }, status=404)
    except Exception as e:
        return Response({
            "message": "Verification Error",
            "SubMessage": str(e)
        }, status=500)