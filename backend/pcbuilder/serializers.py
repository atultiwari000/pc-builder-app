from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """
        Creates and returns a new User instance using the provided validated data.
        
        Parameters:
            validated_data (dict): Data that has been validated for creating a new user.
        
        Returns:
            User: The newly created User instance.
        """
        user = User.objects.create_user(**validated_data)
        return user
    
## Lean API no longer uses ORM models for components; keep only UserSerializer