# ecommerce_integrations/__init__.py
from .base_connector import EcommerceConnector, BaseProductData
from .woocommerce_connector import WooCommerceConnector # Add this line

__all__ = ["EcommerceConnector", "BaseProductData", "WooCommerceConnector"] # Add to __all__
