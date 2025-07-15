# services/service_registry.py
"""Central service registry to avoid circular imports"""

class ServiceRegistry:
    """Singleton service registry"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {}
        return cls._instance
    
    def register(self, name: str, service):
        """Register a service"""
        self._services[name] = service
    
    def get(self, name: str):
        """Get a service"""
        return self._services.get(name)

# Global instance
service_registry = ServiceRegistry()
