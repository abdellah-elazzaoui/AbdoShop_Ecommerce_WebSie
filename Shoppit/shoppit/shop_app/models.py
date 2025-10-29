from django.db import models
from django.utils.text import slugify
# Create your models here.
from django.conf import settings

class Product(models.Model):
    CATEGORY_CHOICES = (
        ('Electronics','ELECTRONICS'),
        ('Sports','SPORTS'),
        ('Clothing','CLOTHING'),
    )
    name = models.CharField(max_length=50,blank=False,null=False)
    slug = models.SlugField(max_length=30,blank=False,null=False)
    image = models.ImageField(upload_to='img')
    description = models.TextField(blank=True,null=False)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    category = models.CharField(max_length=15,choices=CATEGORY_CHOICES,blank=True,null=True)

    def __str__(self):
        return f'{self.name , self.price}' 
    
    def save(self,*args,**kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            while Product.objects.filter(slug=unique_slug).exists():
                unique_slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = unique_slug
        super().save(*args,**kwargs)


class Cart(models.Model):
    cart_code = models.CharField(max_length=11,unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,blank=True,null=True)
    paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,blank=True,null=True)
    modified_at = models.DateTimeField(auto_now=True,blank=True,null=True)

    def __str__(self):
        return self.cart_code
    

class CartItem(models.Model):
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product} in cart {self.cart.id}"
    

class Transaction(models.Model):
    ref = models.CharField(max_length=255,unique=True)
    cart = models.ForeignKey(Cart,on_delete=models.CASCADE,related_name="transactions")
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    currency = models.CharField(max_length=10,default='USD')
    status = models.CharField(max_length=20,default='pending')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction {self.ref} - {self.status}"