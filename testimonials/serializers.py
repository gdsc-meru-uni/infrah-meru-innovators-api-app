from rest_framework import serializers
from .models import Testimonial


class TestimonialSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    class Meta:
        model = Testimonial
        fields = ['id', 'user', 'user_name', 'content', 'rating', 'status', 'created_at']
        read_only_fields = ['user', 'status', 'created_at']


    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    
    def create(self,validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['status'] = Testimonial.APPROVED
        return super().create(validated_data)
    