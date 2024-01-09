import uuid
from typing import Union, Self

from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.db.models.query import QuerySet
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Status(models.IntegerChoices):
    BLOCKED = 0, _('Blocked')
    FOLLOWING = 1, _('Following')


class Relationship(models.Model):
    class Meta:
        verbose_name = _('relationship')
        verbose_name_plural = _('relationships')

    Status = Status

    by = models.ForeignKey(
        'user.User',
        related_name='relationship_by',
        on_delete=models.CASCADE,
        verbose_name=_('relationship from'))
    to = models.ForeignKey(
        'user.User',
        related_name='relationship_to',
        on_delete=models.CASCADE,
        verbose_name=_('relationship to'))

    status = models.IntegerField(
        choices=Status.choices,
        default=Status.FOLLOWING,
        verbose_name=_('status'))

    def clean(self):
        super().clean()
        if self.to == self.by:
            raise ValidationError("User cannot follow self")

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    @property
    def name(self) -> str:
        return _('Relationship from %s to %s') % (self.by.username, self.to.username)


class User(AbstractUser):
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        constraints: tuple = (
            UniqueConstraint(
                Lower('username'),
                name='unique_user_username'),
        )
    id = models.AutoField(primary_key=True, unique=True, )
    name = models.CharField(
        _('name'),
        max_length=65,
        blank=True,
        default=str)
    username = models.CharField(
        _('username'),
        max_length=24,
        unique=True)

    following = models.ManyToManyField(
        'self',
        through='Relationship',
        related_name='followers',
        symmetrical=False)

    # def __relates(self, user: Self, status: Union[int, None] = None) -> Relationship:
    #     if self == user:
    #         raise Exception(_('A user cannot relates it\'s self'))
    #     relation, created = Relationship.objects.get_or_create(
    #         to=user,
    #         by=self,
    #         defaults={
    #             'status': status or Relationship.Status.FOLLOWING,
    #             'to': user,
    #             'by': self})
    #     if not created:
    #         relation.status = status
    #         relation.save()
    #     return relation

    def follow(self, user: Self) -> Relationship:
        relation, created = Relationship.objects.get_or_create(
            to=user,
            by=self,
            status=Relationship.Status.FOLLOWING)
        if created:
            relation.save()
        return relation

    def block_user(self, user: Self) -> Relationship:
        relation, created = Relationship.objects.get_or_create(
            to=user,
            by=self,
            status=Relationship.Status.BLOCKED)
        if created:
            relation.save()
        return relation

    def unfollow(self, user: Self) -> None:
        try:
            relation = Relationship.objects.get(
                by=self,
                to=user)
            relation.delete()
        except User.DoesNotExist:
            raise Exception(_('Relation not found!'))

    def get_blocked_users(self) -> 'QuerySet[Self]':
        return self.following.filter(
            relationship_to__status=Relationship.Status.BLOCKED)

    def get_followers(self, include_blocked_user: bool = False) -> 'QuerySet[Self]':
        if include_blocked_user:
            return self.followers.all()
        return self.followers.exclude(
            models.Q(relationship_by__status=Relationship.Status.BLOCKED) |
            models.Q(relationship_by__by__in=self.get_blocked_users()))

    def get_following(self, include_blocked_user: bool = False) -> 'QuerySet[Self]':
        if include_blocked_user:
            return self.following.all()
        return self.following.exclude(
            models.Q(relationship_to__status=Relationship.Status.BLOCKED) |
            models.Q(relationship_to__to__in=self.get_blocked_users()))

    def get_friends(self, include_blocked_user: bool = False) -> 'QuerySet[Self]':
        if include_blocked_user:
            return self.followers.filter(
                relationship_by__to=self,
                relationship_to__by=self)
        return self.followers.filter(
            relationship_by__to=self,
            relationship_to__by=self,
            relationship_to__status=Relationship.Status.FOLLOWING,
            relationship_by__status=Relationship.Status.FOLLOWING)

    @property
    def count_following(self) -> int:
        return self.get_following().count()

    @property
    def count_blocked_user(self) -> int:
        return self.get_blocked_users().count()

    @property
    def count_friends(self) -> int:
        return self.get_friends().count()

    def im_following(self, user) -> bool:
        return self.following.filter(id=user.id).exists()

    def follows_me(self, user) -> bool:
        return self.followers.filter(id=user.id).exists()
