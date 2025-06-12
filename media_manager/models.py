from typing import Union, TypeVar, Any

# Forward declaration for type hinting MediaItem in MediaItem.from_dict
_MediaItemType = TypeVar('_MediaItemType', bound='MediaItem')

from typing import Union, TypeVar, Any, List

# Forward declaration for type hinting MediaItem in MediaItem.from_dict
_MediaItemType = TypeVar('_MediaItemType', bound='MediaItem')

class MediaItem:
    def __init__(self, id: str, title: str, description: str, item_type: str, tags: List[str] | None = None, thumbnail_path: str | None = None):
        self.id: str = id
        self.title: str = title
        self.description: str = description
        self.item_type: str = item_type
        self.tags: List[str] = tags if tags is not None else []
        self.thumbnail_path: str | None = thumbnail_path

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MediaItem):
            return NotImplemented
        return (self.id == other.id and
                self.title == other.title and
                self.description == other.description and
                self.item_type == other.item_type and
                sorted(self.tags) == sorted(other.tags) and
                self.thumbnail_path == other.thumbnail_path)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'type': self.item_type,
            'tags': self.tags,
            'thumbnail_path': self.thumbnail_path,
        }

    @staticmethod
    def from_dict(item_dict: dict[str, Any]) -> _MediaItemType:
        item_type = item_dict.get('type')
        tags_list = item_dict.get('tags', [])
        if not isinstance(tags_list, list):
            tags_list = []

        thumbnail_path_val = item_dict.get('thumbnail_path')


        common_args = {
            'id': item_dict['id'],
            'title': item_dict['title'],
            'description': item_dict['description'],
            'tags': tags_list,
            'thumbnail_path': thumbnail_path_val
        }

        if item_type == 'video':
            return VideoItem(
                **common_args,
                filepath=item_dict['filepath']
            )
        elif item_type == 'image':
            return ImageItem(
                **common_args,
                filepath=item_dict['filepath']
            )
        elif item_type == 'link':
            # Links typically won't have a 'filepath' but ensure from_dict handles its absence
            common_args.pop('thumbnail_path', None) # Links might not have thumbnails this way
            if 'filepath' in item_dict: # Should not be there for link type from DB
                 del item_dict['filepath']
            return LinkItem(
                **common_args, # Pass only relevant common args
                url=item_dict['url']
            )
        else:
            if 'id' in item_dict and 'title' in item_dict and 'description' in item_dict:
                 return MediaItem( # type: ignore
                    id=item_dict['id'],
                    title=item_dict['title'],
                    description=item_dict['description'],
                    item_type=item_dict.get('type', 'unknown'),
                    tags=tags_list,
                    thumbnail_path=thumbnail_path_val
                )
            raise ValueError(f"Unknown or malformed media type: {item_type} with data {item_dict}")


class VideoItem(MediaItem):
    def __init__(self, id: str, title: str, description: str, filepath: str, tags: List[str] | None = None, thumbnail_path: str | None = None):
        super().__init__(id, title, description, "video", tags, thumbnail_path)
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
    def __init__(self, id: str, title: str, description: str, filepath: str, tags: List[str] | None = None, thumbnail_path: str | None = None):
        super().__init__(id, title, description, "image", tags, thumbnail_path)
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
    def __init__(self, id: str, title: str, description: str, url: str, tags: List[str] | None = None, thumbnail_path: str | None = None): # Links might not have thumbnails
        super().__init__(id, title, description, "link", tags, thumbnail_path)
        self.url: str = url

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LinkItem):
            return NotImplemented
        return super().__eq__(other) and self.url == other.url

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['url'] = self.url
        return data
