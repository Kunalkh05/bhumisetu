/**
 * Compensation calculator UI component.
 *
 * Allows citizens and officers to calculate land acquisition compensation
 * as per RFCTLARR Act 2013, Sections 26-30.
 */

import React, { useState, useMemo } from 'react';
import {
  calculateCompensation,
  formatINR,
  sqmToAcres,
  sqmToGuntha,
  type CompensationInput,
  type CompensationBreakdown,
} from './compensationEngine';

interface FormState {
  landAreaSqm: string;
  circleRatePerSqm: string;
  avgSalePricePerSqm: string;
  isRural: boolean;
  ruralMultiplier: string;
  notificationDate: string;
  awardDate: string;
  structureValue: string;
  cropsAndTreesValue: string;
  resettlementExpenses: string;
}

const initialFormState: FormState = {
  landAreaSqm: '',
  circleRatePerSqm: '',
  avgSalePricePerSqm: '',
  isRural: false,
  ruralMultiplier: '1.0',
  notificationDate: '',
  awardDate: '',
  structureValue: '0',
  cropsAndTreesValue: '0',
  resettlementExpenses: '0',
};

export const CompensationCalculator: React.FC = () => {
  const [form, setForm] = useState<FormState>(initialFormState);
  const [result, setResult] = useState<CompensationBreakdown | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (field: keyof FormState, value: string | boolean) => {
    setForm(prev => ({ ...prev, [field]: value }));
    // Clear error for this field
    setErrors(prev => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!form.landAreaSqm || parseFloat(form.landAreaSqm) <= 0) {
      newErrors.landAreaSqm = 'Land area must be a positive number';
    }
    if (!form.circleRatePerSqm || parseFloat(form.circleRatePerSqm) <= 0) {
      newErrors.circleRatePerSqm = 'Circle rate must be a positive number';
    }
    if (!form.avgSalePricePerSqm || parseFloat(form.avgSalePricePerSqm) <= 0) {
      newErrors.avgSalePricePerSqm = 'Average sale price must be a positive number';
    }
    if (!form.notificationDate) {
      newErrors.notificationDate = 'Notification date is required';
    }
    if (!form.awardDate) {
      newErrors.awardDate = 'Award date is required';
    }
    if (form.notificationDate && form.awardDate && form.awardDate <= form.notificationDate) {
      newErrors.awardDate = 'Award date must be after notification date';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleCalculate = () => {
    if (!validate()) return;

    const input: CompensationInput = {
      landAreaSqm: parseFloat(form.landAreaSqm),
      circleRatePerSqm: parseFloat(form.circleRatePerSqm),
      avgSalePricePerSqm: parseFloat(form.avgSalePricePerSqm),
      isRural: form.isRural,
      ruralMultiplier: parseFloat(form.ruralMultiplier),
      notificationDate: new Date(form.notificationDate),
      awardDate: new Date(form.awardDate),
      structureValue: parseFloat(form.structureValue) || 0,
      cropsAndTreesValue: parseFloat(form.cropsAndTreesValue) || 0,
      resettlementExpenses: parseFloat(form.resettlementExpenses) || 0,
    };

    const breakdown = calculateCompensation(input);
    setResult(breakdown);
  };

  const handleReset = () => {
    setForm(initialFormState);
    setResult(null);
    setErrors({});
  };

  const areaInAcres = useMemo(() => {
    const sqm = parseFloat(form.landAreaSqm);
    if (isNaN(sqm) || sqm <= 0) return null;
    return {
      acres: sqmToAcres(sqm).toFixed(3),
      guntha: sqmToGuntha(sqm).toFixed(2),
    };
  }, [form.landAreaSqm]);

  return (
    <div className="compensation-calculator">
      <div className="calc-header">
        <h2>भूमि अधिग्रहण मुआवजा कैलकुलेटर</h2>
        <h3>Land Acquisition Compensation Calculator</h3>
        <p className="calc-subtitle">
          As per RFCTLARR Act 2013, Sections 26-30
        </p>
      </div>

      <div className="calc-form">
        <div className="form-section">
          <h4>Land Details</h4>

          <div className="form-group">
            <label htmlFor="landAreaSqm">Land Area (sq meters) *</label>
            <input
              id="landAreaSqm"
              type="number"
              value={form.landAreaSqm}
              onChange={e => handleChange('landAreaSqm', e.target.value)}
              placeholder="Enter land area in square meters"
              min="0"
              step="0.01"
            />
            {areaInAcres && (
              <span className="unit-hint">
                ≈ {areaInAcres.acres} acres / {areaInAcres.guntha} guntha
              </span>
            )}
            {errors.landAreaSqm && <span className="error">{errors.landAreaSqm}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="circleRatePerSqm">Circle Rate (₹/sq m) *</label>
            <input
              id="circleRatePerSqm"
              type="number"
              value={form.circleRatePerSqm}
              onChange={e => handleChange('circleRatePerSqm', e.target.value)}
              placeholder="Government registered rate per sq meter"
              min="0"
            />
            {errors.circleRatePerSqm && <span className="error">{errors.circleRatePerSqm}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="avgSalePricePerSqm">Average Sale Price (₹/sq m) *</label>
            <input
              id="avgSalePricePerSqm"
              type="number"
              value={form.avgSalePricePerSqm}
              onChange={e => handleChange('avgSalePricePerSqm', e.target.value)}
              placeholder="Average from recent sale transactions"
              min="0"
            />
            {errors.avgSalePricePerSqm && <span className="error">{errors.avgSalePricePerSqm}</span>}
          </div>

          <div className="form-group checkbox-group">
            <input
              id="isRural"
              type="checkbox"
              checked={form.isRural}
              onChange={e => handleChange('isRural', e.target.checked)}
            />
            <label htmlFor="isRural">Rural Area (Section 26(1)(b) multiplier applies)</label>
          </div>

          {form.isRural && (
            <div className="form-group">
              <label htmlFor="ruralMultiplier">Rural Multiplier (1.0 - 2.0)</label>
              <input
                id="ruralMultiplier"
                type="number"
                value={form.ruralMultiplier}
                onChange={e => handleChange('ruralMultiplier', e.target.value)}
                min="1.0"
                max="2.0"
                step="0.1"
              />
            </div>
          )}
        </div>

        <div className="form-section">
          <h4>Timeline</h4>

          <div className="form-group">
            <label htmlFor="notificationDate">Section 11 Notification Date *</label>
            <input
              id="notificationDate"
              type="date"
              value={form.notificationDate}
              onChange={e => handleChange('notificationDate', e.target.value)}
            />
            {errors.notificationDate && <span className="error">{errors.notificationDate}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="awardDate">Section 23 Award Date *</label>
            <input
              id="awardDate"
              type="date"
              value={form.awardDate}
              onChange={e => handleChange('awardDate', e.target.value)}
            />
            {errors.awardDate && <span className="error">{errors.awardDate}</span>}
          </div>
        </div>

        <div className="form-section">
          <h4>Additional Compensation</h4>

          <div className="form-group">
            <label htmlFor="structureValue">Value of Structures (₹)</label>
            <input
              id="structureValue"
              type="number"
              value={form.structureValue}
              onChange={e => handleChange('structureValue', e.target.value)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label htmlFor="cropsAndTreesValue">Crops & Trees Value (₹)</label>
            <input
              id="cropsAndTreesValue"
              type="number"
              value={form.cropsAndTreesValue}
              onChange={e => handleChange('cropsAndTreesValue', e.target.value)}
              min="0"
            />
          </div>

          <div className="form-group">
            <label htmlFor="resettlementExpenses">Resettlement Expenses (₹)</label>
            <input
              id="resettlementExpenses"
              type="number"
              value={form.resettlementExpenses}
              onChange={e => handleChange('resettlementExpenses', e.target.value)}
              min="0"
            />
          </div>
        </div>

        <div className="calc-actions">
          <button className="btn-calculate" onClick={handleCalculate}>
            Calculate Compensation
          </button>
          <button className="btn-reset" onClick={handleReset}>
            Reset
          </button>
        </div>
      </div>

      {result && (
        <div className="calc-results">
          <h4>Compensation Breakdown</h4>

          <table className="results-table">
            <tbody>
              <tr>
                <td>Market Value per sq m</td>
                <td className="amount">{formatINR(result.marketValuePerSqm)}</td>
              </tr>
              {result.appliedRuralMultiplier > 1.0 && (
                <tr>
                  <td>Rural Multiplier Applied</td>
                  <td className="amount">{result.appliedRuralMultiplier.toFixed(1)}x</td>
                </tr>
              )}
              <tr>
                <td>Total Market Value (Section 26)</td>
                <td className="amount">{formatINR(result.totalMarketValue)}</td>
              </tr>
              <tr>
                <td>Solatium — 100% (Section 30(1))</td>
                <td className="amount">{formatINR(result.solatium)}</td>
              </tr>
              <tr>
                <td>Additional Compensation — 12% p.a. for {result.monthsBetween} months (Section 30(3))</td>
                <td className="amount">{formatINR(result.additionalCompensation)}</td>
              </tr>
              {result.assetsValue > 0 && (
                <tr>
                  <td>Structures, Crops & Trees</td>
                  <td className="amount">{formatINR(result.assetsValue)}</td>
                </tr>
              )}
              {result.rehabilitationCosts > 0 && (
                <tr>
                  <td>Rehabilitation & Resettlement</td>
                  <td className="amount">{formatINR(result.rehabilitationCosts)}</td>
                </tr>
              )}
              <tr className="total-row">
                <td><strong>Total Compensation Payable</strong></td>
                <td className="amount total">{formatINR(result.totalCompensation)}</td>
              </tr>
            </tbody>
          </table>

          <p className="disclaimer">
            * This is an indicative calculation based on RFCTLARR Act 2013.
            Actual compensation may vary based on collector's assessment
            and applicable state-specific rules.
          </p>
        </div>
      )}
    </div>
  );
};

export default CompensationCalculator;
