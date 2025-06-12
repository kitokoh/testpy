from typing import Union, TypeVar, Any

# Forward declaration for type hinting MediaItem in MediaItem.from_dict
_MediaItemType = TypeVar('_MediaItemType', bound='MediaItem')

class MediaItem:
    def __init__(self, id: str, title: str, description: str, category: str, item_type: str):
        self.id: str = id
        self.title: str = title
        self.description: str = description
        self.category: str = category
        self.item_type: str = item_type # Renamed from 'type'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MediaItem):
            return NotImplemented
        return (self.id == other.id and
                self.title == other.title and
                self.description == other.description and
                self.category == other.category and
                self.item_type == other.item_type)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'type': self.item_type, # Ensure this key is 'type' for serialization
        }

    @staticmethod
    def from_dict(item_dict: dict[str, Any]) -> _MediaItemType:
        item_type = item_dict.get('type')
        if item_type == 'video':
            return VideoItem(
                id=item_dict['id'],
                title=item_dict['title'],
                description=item_dict['description'],
                category=item_dict['category'],
                filepath=item_dict['filepath']
            )
        elif item_type == 'image':
            return ImageItem(
                id=item_dict['id'],
                title=item_dict['title'],
                description=item_dict['description'],
                category=item_dict['category'],
                filepath=item_dict['filepath']
            )
        elif item_type == 'link':
            return LinkItem(
                id=item_dict['id'],
                title=item_dict['title'],
                description=item_dict['description'],
                category=item_dict['category'],
                url=item_dict['url']
            )
        else:
            # Fallback or error for unknown type.
            # For now, let's try to create a base MediaItem if common fields are present,
            # or raise an error if that's not desired.
            # raise ValueError(f"Unknown media type: {item_type}")
            # Alternatively, return a base MediaItem if it makes sense.
            # This part depends on desired error handling for unknown types.
            # For strictness, raising ValueError is better.
            if 'id' in item_dict and 'title' in item_dict and 'description' in item_dict and 'category' in item_dict:
                 return MediaItem(
                    id=item_dict['id'],
                    title=item_dict['title'],
                    description=item_dict['description'],
                    category=item_dict['category'],
                    item_type=item_dict.get('type', 'unknown') # Store original type or 'unknown'
                )
            raise ValueError(f"Unknown or malformed media type: {item_type}")


class VideoItem(MediaItem):
    def __init__(self, id: str, title: str, description: str, category: str, filepath: str):
        super().__init__(id, title, description, category, "video") # Explicitly pass 'video'
        self.filepath: str = filepath

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VideoItem):
            return NotImplemented
        return super().__eq__(other) and self.filepath == other.filepath

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['filepath'] = self.filepath
        return data

class ImageItem(MediaItem):
    def __init__(self, id: str, title: str, description: str, category: str, filepath: str):
        super().__init__(id, title, description, category, "image") # Explicitly pass 'image'
        self.filepath: str = filepath

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ImageItem):
            return NotImplemented
        return super().__eq__(other) and self.filepath == other.filepath

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['filepath'] = self.filepath
        return data

class LinkItem(MediaItem):
    def __init__(self, id: str, title: str, description: str, category: str, url: str):
        super().__init__(id, title, description, category, "link") # Explicitly pass 'link'
        self.url: str = url

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LinkItem):
            return NotImplemented
        return super().__eq__(other) and self.url == other.url

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['url'] = self.url
        return data
