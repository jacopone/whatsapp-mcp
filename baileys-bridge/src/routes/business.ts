import { Router, Request, Response } from 'express';
import type { WASocket } from '@whiskeysockets/baileys';

// T052: Business Catalog Endpoints

interface BusinessCatalogResponse {
  success: boolean;
  message?: string;
  catalog?: any;
  product_count?: number;
}

interface BusinessProductResponse {
  success: boolean;
  message?: string;
  product?: any;
}

export function registerBusinessRoutes(
  router: Router,
  getSock: () => ReturnType<typeof import('@whiskeysockets/baileys').default> | null
) {
  // Get business catalog
  router.get('/business/:jid/catalog', async (req: Request, res: Response) => {
    const sock = getSock();

    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'Not connected to WhatsApp'
      });
    }

    const { jid } = req.params;

    if (!jid) {
      return res.status(400).json({
        success: false,
        message: 'jid parameter is required'
      });
    }

    try {
      // Request business catalog from WhatsApp
      // Note: Baileys has better support for business catalog operations
      const catalog = await sock.getBusinessProfile(jid);

      if (!catalog) {
        return res.json({
          success: true,
          message: 'No catalog found for this business account',
          catalog: null,
          product_count: 0
        });
      }

      // Extract catalog information
      const response: BusinessCatalogResponse = {
        success: true,
        catalog: catalog,
        product_count: catalog.products ? catalog.products.length : 0
      };

      res.json(response);
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Failed to get business catalog',
        error: String(error)
      });
    }
  });

  // Get product details from catalog
  router.get('/business/:jid/catalog/:product_id', async (req: Request, res: Response) => {
    const sock = getSock();

    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'Not connected to WhatsApp'
      });
    }

    const { jid, product_id } = req.params;

    if (!jid || !product_id) {
      return res.status(400).json({
        success: false,
        message: 'jid and product_id parameters are required'
      });
    }

    try {
      // First get the catalog
      const catalog = await sock.getBusinessProfile(jid);

      if (!catalog || !catalog.products) {
        return res.status(404).json({
          success: false,
          message: 'Catalog or products not found'
        });
      }

      // Find the specific product
      const product = catalog.products.find((p: any) => p.id === product_id);

      if (!product) {
        return res.status(404).json({
          success: false,
          message: `Product with ID ${product_id} not found in catalog`
        });
      }

      // Return product details
      const response: BusinessProductResponse = {
        success: true,
        product: {
          id: product.id,
          name: product.name,
          description: product.description,
          price: product.price,
          currency: product.currency,
          images: product.images || [],
          availability: product.availability || 'in_stock',
          retailer_id: product.retailerId
        }
      };

      res.json(response);
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Failed to get product details',
        error: String(error)
      });
    }
  });
}
