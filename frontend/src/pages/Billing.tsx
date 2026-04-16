import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CreditCard,
  Check,
  Zap,
  Building2,
  GraduationCap,
  Crown,
  Receipt,
  Download,
  Calendar,
  ChevronRight,
  AlertCircle,
  Sparkles,
  Users,
  FileCheck,
} from 'lucide-react';
import Icon from '@/components/Icon';
import Button from '@/components/Button';
import Breadcrumbs from '@/components/Breadcrumbs';
import { useAuth } from '@/contexts/AuthContext';

interface PricingPlan {
  id: string;
  name: string;
  pricePerStudent: number;
  minStudents: number;
  description: string;
  features: string[];
  highlighted?: boolean;
  icon: React.ElementType;
  color: string;
}

interface Invoice {
  id: string;
  date: string;
  amount: number;
  status: 'paid' | 'pending' | 'overdue';
  description: string;
  studentCount: number;
}

const pricingPlans: PricingPlan[] = [
  {
    id: 'starter',
    name: 'Starter',
    pricePerStudent: 0,
    minStudents: 100,
    description: 'Free 90-day trial for new institutions',
    icon: GraduationCap,
    color: 'from-green-500 to-green-600',
    features: [
      'Up to 500 students',
      'Unlimited lecturers',
      'Basic AI grading (500 credits)',
      'Email support',
      'Standard analytics',
      'Mobile-friendly exams',
      'No credit card required',
      '90-day free trial',
    ],
  },
  {
    id: 'intermediate',
    name: 'Intermediate',
    pricePerStudent: 1000,
    minStudents: 500,
    description: 'Perfect for growing institutions',
    icon: Building2,
    color: 'from-blue-500 to-blue-600',
    highlighted: true,
    features: [
      'Up to 5,000 students',
      'Unlimited lecturers',
      'Enhanced AI grading (10,000 credits/semester)',
      'Priority support',
      'Advanced analytics & reports',
      'Paper exam scanning',
      'Custom branding',
      'API access',
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    pricePerStudent: 2500,
    minStudents: 1000,
    description: 'For large institutions with complex needs',
    icon: Crown,
    color: 'from-purple-500 to-purple-600',
    features: [
      'Unlimited students',
      'Unlimited everything',
      'Premium AI grading (unlimited)',
      '24/7 dedicated support',
      'Full analytics suite',
      'On-premise deployment option',
      'Custom integrations',
      'SLA guarantee',
      'Dedicated account manager',
    ],
  },
];

const mockInvoices: Invoice[] = [
  {
    id: 'INV-2024-001',
    date: '2024-09-01',
    amount: 2500000,
    status: 'paid',
    description: 'Fall Semester 2024 - 2,500 students',
    studentCount: 2500,
  },
  {
    id: 'INV-2024-002',
    date: '2025-01-15',
    amount: 2500000,
    status: 'pending',
    description: 'Spring Semester 2025 - 2,500 students',
    studentCount: 2500,
  },
];

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
    minimumFractionDigits: 0,
  }).format(amount);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-NG', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function PlanCard({ plan, isCurrent }: { plan: PricingPlan; isCurrent: boolean }) {
  const IconComponent = plan.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`surface-card p-6 relative overflow-hidden ${
        plan.highlighted ? 'ring-2 ring-[var(--color-primary-500)]' : ''
      }`}
    >
      {plan.highlighted && (
        <div className="absolute top-0 right-0 bg-[var(--color-primary-600)] text-white text-xs font-semibold px-3 py-1 rounded-bl-lg">
          Most Popular
        </div>
      )}

      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${plan.color} flex items-center justify-center mb-4`}>
        <Icon as={IconComponent} size={24} className="text-white" />
      </div>

      <h3 className="text-xl font-bold text-[var(--color-text-primary)]">{plan.name}</h3>
      <p className="text-sm text-[var(--color-text-secondary)] mt-1">{plan.description}</p>

      <div className="mt-4 mb-6">
        {plan.pricePerStudent === 0 ? (
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-[var(--color-text-primary)]">
              FREE
            </span>
            <span className="text-[var(--color-text-secondary)]">for 90 days</span>
          </div>
        ) : (
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-[var(--color-text-primary)]">
              ₦{plan.pricePerStudent.toLocaleString()}
            </span>
            <span className="text-[var(--color-text-secondary)]">/student/semester</span>
          </div>
        )}
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Minimum {plan.minStudents.toLocaleString()} students
        </p>
      </div>

      <div className="space-y-3 mb-6">
        {plan.features.map((feature, idx) => (
          <div key={idx} className="flex items-start gap-3">
            <div className="w-5 h-5 rounded-full bg-[var(--color-success-100)] flex items-center justify-center flex-shrink-0 mt-0.5">
              <Icon as={Check} size={12} className="text-[var(--color-success-600)]" />
            </div>
            <span className="text-sm text-[var(--color-text-secondary)]">{feature}</span>
          </div>
        ))}
      </div>

      <Button
        variant={isCurrent ? 'secondary' : plan.highlighted ? 'primary' : 'secondary'}
        className="w-full"
        disabled={isCurrent}
      >
        {isCurrent ? 'Current Plan' : 'Upgrade'}
      </Button>
    </motion.div>
  );
}

function UsageCard() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const usageStats = {
    totalStudents: 2500,
    examsGraded: 1247,
    currentPlan: 'Intermediate',
    nextBillingDate: '2025-06-01',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="surface-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Current Usage</h3>
        <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
          <Icon as={Calendar} size={16} />
          <span>Next billing: {formatDate(usageStats.nextBillingDate)}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-[var(--color-bg-secondary)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Icon as={Users} size={18} className="text-[var(--color-primary-600)]" />
            <span className="text-sm text-[var(--color-text-secondary)]">Students</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {usageStats.totalStudents.toLocaleString()}
          </p>
        </div>

        <div className="bg-[var(--color-bg-secondary)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Icon as={FileCheck} size={18} className="text-[var(--color-success-600)]" />
            <span className="text-sm text-[var(--color-text-secondary)]">Exams Graded</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {usageStats.examsGraded.toLocaleString()}
          </p>
        </div>

        <div className="bg-[var(--color-bg-secondary)] rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <Icon as={Zap} size={18} className="text-[var(--color-warning-600)]" />
            <span className="text-sm text-[var(--color-text-secondary)]">Plan</span>
          </div>
          <p className="text-lg font-bold text-[var(--color-text-primary)]">{usageStats.currentPlan}</p>
        </div>
      </div>

      {isAdmin && (
        <div className="mt-4 pt-4 border-t border-[var(--color-border-light)]">
          <div className="flex items-center justify-between">
            <Button variant="secondary" className="flex items-center gap-2">
              <Icon as={Receipt} size={16} />
              View Invoice
            </Button>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function InvoiceList() {
  const getStatusBadge = (status: Invoice['status']) => {
    const styles = {
      paid: 'bg-[var(--color-success-100)] text-[var(--color-success-700)]',
      pending: 'bg-[var(--color-warning-100)] text-[var(--color-warning-700)]',
      overdue: 'bg-[var(--color-error-100)] text-[var(--color-error-700)]',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="surface-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Billing History</h3>
        <Button variant="ghost" className="text-sm">
          View All
          <Icon as={ChevronRight} size={16} className="ml-1" />
        </Button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--color-border-light)]">
              <th className="text-left py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Invoice
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Date
              </th>
              <th className="text-left py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Students
              </th>
              <th className="text-right py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Amount
              </th>
              <th className="text-center py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Status
              </th>
              <th className="text-right py-3 px-4 text-sm font-medium text-[var(--color-text-secondary)]">
                Action
              </th>
            </tr>
          </thead>
          <tbody>
            {mockInvoices.map((invoice) => (
              <tr key={invoice.id} className="border-b border-[var(--color-border-light)] last:border-0">
                <td className="py-4 px-4">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[var(--color-bg-secondary)] flex items-center justify-center">
                      <Icon as={Receipt} size={16} className="text-[var(--color-text-secondary)]" />
                    </div>
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">
                      {invoice.id}
                    </span>
                  </div>
                </td>
                <td className="py-4 px-4 text-sm text-[var(--color-text-secondary)]">
                  {formatDate(invoice.date)}
                </td>
                <td className="py-4 px-4 text-sm text-[var(--color-text-secondary)]">
                  {invoice.studentCount.toLocaleString()}
                </td>
                <td className="py-4 px-4 text-right text-sm font-medium text-[var(--color-text-primary)]">
                  {formatCurrency(invoice.amount)}
                </td>
                <td className="py-4 px-4 text-center">{getStatusBadge(invoice.status)}</td>
                <td className="py-4 px-4 text-right">
                  <Button variant="ghost" className="p-2">
                    <Icon as={Download} size={16} />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}

function PaymentMethodCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="surface-card p-6"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-[var(--color-primary-100)] flex items-center justify-center">
          <Icon as={CreditCard} size={20} className="text-[var(--color-primary-600)]" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">Payment Method</h3>
          <p className="text-sm text-[var(--color-text-secondary)]">Manage your billing preferences</p>
        </div>
      </div>

      <div className="bg-[var(--color-bg-secondary)] rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-6 bg-gradient-to-r from-[var(--color-primary-500)] to-[var(--color-primary-600)] rounded flex items-center justify-center">
              <span className="text-white text-xs font-bold">VISA</span>
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--color-text-primary)]">•••• 4242</p>
              <p className="text-xs text-[var(--color-text-muted)]">Expires 12/25</p>
            </div>
          </div>
          <span className="px-2 py-1 rounded-full text-xs font-medium bg-[var(--color-success-100)] text-[var(--color-success-700)]">
            Default
          </span>
        </div>
      </div>

      <div className="flex gap-3">
        <Button variant="secondary" className="flex-1">
          Add Card
        </Button>
        <Button variant="ghost">Edit</Button>
      </div>

      <div className="mt-4 pt-4 border-t border-[var(--color-border-light)]">
        <div className="flex items-start gap-3 text-sm text-[var(--color-text-secondary)]">
          <Icon as={AlertCircle} size={16} className="mt-0.5 flex-shrink-0" />
          <p>
            Nigerian universities typically pay via bank transfer. Contact us to set up direct debit
            or invoice-based billing.
          </p>
        </div>
      </div>
    </motion.div>
  );
}

export default function BillingPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [activeTab, setActiveTab] = useState<'plans' | 'usage'>('plans');

  return (
    <div className="page-container">
      <Breadcrumbs />

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] mb-2">
          Billing & Plans
        </h1>
        <p className="text-[var(--color-text-secondary)]">
          Manage your subscription, view usage, and handle payments
        </p>
      </div>

      {isAdmin && (
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('plans')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'plans'
                ? 'bg-[var(--color-primary-600)] text-white'
                : 'bg-[var(--color-bg-card)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
            }`}
          >
            <Icon as={Sparkles} size={16} className="inline mr-2" />
            Plans & Pricing
          </button>
          <button
            onClick={() => setActiveTab('usage')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'usage'
                ? 'bg-[var(--color-primary-600)] text-white'
                : 'bg-[var(--color-bg-card)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-hover)]'
            }`}
          >
            <Icon as={Zap} size={16} className="inline mr-2" />
            Usage & Billing
          </button>
        </div>
      )}

      {activeTab === 'plans' ? (
        <>
          <div className="mb-6 p-4 bg-[var(--color-primary-50)] border border-[var(--color-primary-200)] rounded-lg">
            <div className="flex items-start gap-3">
              <Icon as={Sparkles} size={20} className="text-[var(--color-primary-600)] mt-0.5" />
              <div>
                <h3 className="font-semibold text-[var(--color-primary-800)] mb-1">
                  Simple, Transparent Pricing
                </h3>
                <p className="text-sm text-[var(--color-primary-700)]">
                  Start free for 90 days. Then upgrade to Intermediate (₦1,000/student) 
                  or Enterprise (₦2,500/student) based on your needs.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            {pricingPlans.map((plan) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                isCurrent={plan.name === 'Intermediate'}
              />
            ))}
          </div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="surface-card p-6"
          >
            <h3 className="text-lg font-semibold text-[var(--color-text-primary)] mb-4">
              Frequently Asked Questions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  q: 'How does the 90-day free trial work?',
                  a: 'Start with full Starter features for 90 days. No credit card required. Upgrade anytime.',
                },
                {
                  q: 'What happens after the trial ends?',
                  a: 'Choose Intermediate (₦1,000/student) or Enterprise (₦2,500/student). We\'ll help you migrate.',
                },
                {
                  q: 'What\'s the difference between Intermediate and Enterprise?',
                  a: 'Enterprise includes unlimited students, unlimited AI grading, on-premise option, and 24/7 support.',
                },
                {
                  q: 'Can we switch plans mid-semester?',
                  a: 'Yes, you can upgrade anytime. Downgrades take effect next semester.',
                },
              ].map((faq, idx) => (
                <div key={idx} className="space-y-1">
                  <p className="font-medium text-[var(--color-text-primary)]">{faq.q}</p>
                  <p className="text-sm text-[var(--color-text-secondary)]">{faq.a}</p>
                </div>
              ))}
            </div>
          </motion.div>
        </>
      ) : (
        <div className="space-y-6">
          <UsageCard />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <InvoiceList />
            </div>
            <div>
              <PaymentMethodCard />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
