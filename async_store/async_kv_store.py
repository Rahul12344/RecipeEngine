from abc import ABC, abstractmethod
from typing import TypeVar, Optional, Generic

K = TypeVar('K')
V = TypeVar('V')

class AsyncKVStore(ABC, Generic[K, V]):
    """
    Abstract base class for asynchronous key-value storage.
    Supports basic get and set operations with arbitrary key and value types.
    """

    @abstractmethod
    async def get(self, key: K) -> Optional[V]:
        """
        Retrieve a value by key.

        Args:
            key: The key to look up

        Returns:
            The value associated with the key, or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: K, value: V) -> None:
        """
        Store a value with the given key.

        Args:
            key: The key to store the value under
            value: The value to store
        """
        pass

    @abstractmethod
    async def delete(self, key: K) -> bool:
        """
        Delete a key-value pair.

        Args:
            key: The key to delete

        Returns:
            True if the key was deleted, False if it didn't exist
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the store and release any resources.
        """
        pass

