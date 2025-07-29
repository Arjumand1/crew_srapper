import random
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'username')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8  # Only keep minimum length validation
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'name')  # Removed username

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        # Remove password2 as it's not a model field
        validated_data.pop('password2', None)

        # Extract the part before @ from email to use as base for username
        email_username = validated_data['email'].split('@')[0]

        # Keep trying until we find an available username
        max_attempts = 10
        for _ in range(max_attempts):
            # Generate a random 4-digit suffix
            random_suffix = str(random.randint(1000, 9999))
            username = f"{email_username}{random_suffix}"

            # Check if username already exists
            if not User.objects.filter(username=username).exists():
                # Create the user with the validated data
                user = User.objects.create(
                    username=username,
                    email=validated_data['email'],
                    name=validated_data['name']
                )
                # Set the password (this will handle hashing)
                user.set_password(validated_data['password'])
                user.save()
                return user

        # If we've exhausted all attempts, raise an error
        raise serializers.ValidationError(
            "Could not create a unique username. Please try again with a different email."
        )
