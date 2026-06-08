import { Parser as ExprParser } from "expr-eval";

/** Single shared expression parser — expr-eval Parser instances are stateless
 * and can be reused across all ComputedValue nodes. */
export const FORMULA_PARSER = new ExprParser();
