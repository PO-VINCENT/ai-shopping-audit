// Bridges the dependency-free ES-module engine into the classic popup script.
import * as Engine from './engine.mjs';
globalThis.CR = Engine;
