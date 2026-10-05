import { describe, expect, it } from 'vitest';

describe('MeetMind frontend test harness', () => {
  it('supports the expected demo meeting identity', () => {
    const meeting = { id: 'apollo-demo', label: 'Project Apollo · Sprint Planning', demo: true };
    expect(meeting.demo).toBe(true);
    expect(meeting.label).toContain('Apollo');
  });
});
