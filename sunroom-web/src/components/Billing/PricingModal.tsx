
'use client';

import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from '@/components/AuthContext';
import { getApiUrl } from '@/lib/utils';

const API_URL = getApiUrl();

// TODO: Replace these with your actual Stripe Price IDs
const tiers = [
  {
    name: 'Free',
    price: '$0',
    description: 'For getting started and exploring.',
    features: ['5 audio minutes/month', '10,000 LLM tokens/month', 'Limited Generations'],
    isCurrent: true,
  },
  {
    name: 'Pro',
    price: '$25',
    description: 'For power users and professionals.',
    features: ['Unlimited audio minutes', '1,000,000 LLM tokens/month', 'Unlimited Generations'],
    priceId: 'price_123456789_PRO', // <--- REPLACE THIS
    isCurrent: false,
  },
];

interface PricingModalProps {
  onClose: () => void;
}

export const PricingModal: React.FC<PricingModalProps> = ({ onClose }) => {
  const [loadingPriceId, setLoadingPriceId] = useState<string | null>(null);
  const { session } = useAuth();

  const handleSubscribe = async (priceId: string) => {
    if (!session) {
      console.error("No active session. Please log in.");
      return;
    }
    setLoadingPriceId(priceId);
    try {
      const token = session.access_token;
      const response = await axios.post(
        `${API_URL}/api/v1/billing/create-checkout-session`,
        { price_id: priceId },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      // Redirect to Stripe's checkout page
      window.location.href = response.data.url;
    } catch (error) {
      console.error("Failed to create checkout session:", error);
      setLoadingPriceId(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 z-50 flex justify-center items-center">
      <div className="bg-gray-900 rounded-lg shadow-xl p-8 max-w-2xl w-full border border-gray-700">
        <h2 className="text-2xl font-bold text-center mb-6">Choose Your Plan</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {tiers.map((tier) => (
            <div key={tier.name} className={`p-6 rounded-lg border ${tier.isCurrent ? 'border-purple-500' : 'border-gray-700'}`}>
              <h3 className="text-lg font-bold">{tier.name}</h3>
              <p className="text-3xl font-bold my-2">{tier.price}<span className="text-sm font-normal">/mo</span></p>
              <p className="text-gray-400 text-sm mb-4">{tier.description}</p>
              <ul className="text-sm space-y-2 mb-6">
                {tier.features.map(feat => <li key={feat}>✓ {feat}</li>)}
              </ul>
              {tier.priceId && (
                <button
                  onClick={() => handleSubscribe(tier.priceId!)}
                  disabled={!!loadingPriceId}
                  className="w-full bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-md font-medium transition-all disabled:bg-gray-600"
                >
                  {loadingPriceId === tier.priceId ? 'Redirecting...' : 'Subscribe'}
                </button>
              )}
            </div>
          ))}
        </div>
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white">&times;</button>
      </div>
    </div>
  );
};
