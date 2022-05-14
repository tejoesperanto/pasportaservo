from abc import ABC, abstractmethod


class PlaceFilter(ABC):
    def __init__(self, restrained_search):
        self.restrained_search = restrained_search

    def __call__(self, place):
        return self.filter(place)

    @abstractmethod
    def filter(self, place):  # pragma: no cover
        pass


class OkForGuestsFilter(PlaceFilter):
    """
    Filters owned places where the user either hosts or meets guests.
    """
    check_hosting = True
    check_meeting = True

    def filter(self, place):
        # Return whether the owned place is where the user either hosts or meets guests.
        return (
            any([
                place.available if self.check_hosting else None,
                (place.tour_guide or place.have_a_drink) if self.check_meeting else None,
            ])
            # ... and is visible to the public.
            and (place.visibility__visible_online_public if self.restrained_search else True)
        )


class HostingFilter(OkForGuestsFilter):
    """
    Filters owned places where the user hosts.
    """
    check_hosting = True
    check_meeting = False


class MeetingFilter(OkForGuestsFilter):
    """
    Filters owned places where the user is ready to meet up with guests.
    """
    check_hosting = False
    check_meeting = True


class InBookFilter(PlaceFilter):
    """
    Filters owned places selected to appear in the printed edition.
    """
    def filter(self, place):
        # Return whether the owned place is selected to appear in the printed edition.
        return (
            place.available and place.in_book
            # ... and not (temporarily) hidden for publication.
            and (place.visibility__visible_in_book if self.restrained_search else True)
        )


class OkForBookFilter(PlaceFilter):
    """
    Filters owned places that were confirmed by the host or approved by a supervisor.
    """
    def __init__(self, *args, **kwargs):
        self.accept_confirmed = kwargs['accept_confirmed']
        self.accept_approved = kwargs['accept_approved']
        if not self.accept_confirmed and not self.accept_approved:
            self.book_filter = lambda place: True  # Ignore filter.
        super().__init__(*args)

    def book_filter(self, place):
        return any([
            place.confirmed if self.accept_confirmed else None,
            place.checked if self.accept_approved else None,
        ])

    def filter(self, place):
        # Return whether the owned place was confirmed by the host or approved by a supervisor.
        return (
            self.book_filter(place) and place.available and place.in_book
            and place.visibility__visible_in_book
        )
