/**
 * Calculator module barrel export.
 */

export { CompensationCalculator } from './CompensationCalculator';
export {
  calculateCompensation,
  formatINR,
  sqmToAcres,
  sqmToHectares,
  sqmToGuntha,
  sqmToBigha,
} from './compensationEngine';
export type {
  CompensationInput,
  CompensationBreakdown,
} from './compensationEngine';
