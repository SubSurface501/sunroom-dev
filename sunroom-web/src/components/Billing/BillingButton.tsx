
'use client';

import React, { useState } from 'react';
import { PricingModal } from './PricingModal';

export const BillingButton: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-md font-medium shadow-lg transition-all"
      >
        Billing
      </button>
      {isModalOpen && <PricingModal onClose={() => setIsModalOpen(false)} />}
    </>
  );
};
