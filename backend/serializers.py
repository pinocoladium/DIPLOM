from rest_framework import serializers

from backend.models import Client, Contact
      
class ContactsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }
        
class ClientSerializer(serializers.ModelSerializer):
    
    contacts = ContactsSerializer(read_only=True, many=True)
    
    class Meta:
        model = Client
        fields = ('id', 'first_name', 'last_name', 'username', 'email', 'company', 'position', 'contacts')
        read_only_fields = ('id',)