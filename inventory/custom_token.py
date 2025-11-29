# E:\study\worker_inventory\worker_inventory_backend\inventory\custom_token.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_staff'] = user.is_staff
        token['username'] = user.username
        token['user_id'] = user.id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # ADD EXTRA FIELDS TO RESPONSE BODY
        data['is_staff'] = self.user.is_staff
        data['username'] = self.user.username
        data['user_id'] = self.user.id

        return data


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer
