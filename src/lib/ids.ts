let centreCounter = 1;
let childCounter = 1;
let counter = 1;

export function nextCentreSystemId(): string {
  return `CTR-${String(centreCounter++).padStart(3, '0')}`;
}

export function nextChildSystemId(): string {
  return `CHD-${String(childCounter++).padStart(5, '0')}`;
}

export function uid(prefix = 'id'): string {
  return `${prefix}_${counter++}_${Math.random().toString(36).slice(2, 8)}`;
}

export function _resetIdsForTests(): void {
  centreCounter = 1;
  childCounter = 1;
  counter = 1;
}
