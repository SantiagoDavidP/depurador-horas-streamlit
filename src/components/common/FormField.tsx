import React from 'react';
import { cn } from '@/utils';

interface FormFieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export const FormField: React.FC<FormFieldProps> = ({
  label,
  htmlFor,
  error,
  required,
  children,
  className,
}) => {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label
        htmlFor={htmlFor}
        className="block text-sm font-medium text-slate-700"
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      {error && (
        <p className="text-xs text-red-600 mt-1">{error}</p>
      )}
    </div>
  );
};

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
  leftIcon?: React.ReactNode;
  rightAction?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  hasError,
  leftIcon,
  rightAction,
  className,
  ...props
}) => {
  return (
    <div className="relative">
      {leftIcon && (
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
          {leftIcon}
        </span>
      )}
      <input
        className={cn(
          'w-full px-3 py-2.5 border rounded-lg text-sm transition-all focus:outline-none focus:ring-2',
          leftIcon && 'pl-10',
          rightAction && 'pr-10',
          hasError
            ? 'border-red-300 focus:ring-red-500/20 focus:border-red-500'
            : 'border-slate-300 focus:ring-blue-700/20 focus:border-blue-700',
          className
        )}
        {...props}
      />
      {rightAction && (
        <span className="absolute right-2 top-1/2 -translate-y-1/2">
          {rightAction}
        </span>
      )}
    </div>
  );
};

interface SelectFieldProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
  options: Array<{ value: string; label: string }>;
  placeholder?: string;
}

export const SelectField: React.FC<SelectFieldProps> = ({
  hasError,
  options,
  placeholder,
  className,
  ...props
}) => {
  return (
    <select
      className={cn(
        'w-full px-3 py-2.5 border rounded-lg text-sm transition-all focus:outline-none focus:ring-2 cursor-pointer bg-white',
        hasError
          ? 'border-red-300 focus:ring-red-500/20 focus:border-red-500'
          : 'border-slate-300 focus:ring-blue-700/20 focus:border-blue-700',
        className
      )}
      {...props}
    >
      {placeholder && (
        <option value="">{placeholder}</option>
      )}
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
};
