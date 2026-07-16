import { buildGraphElements } from '../src/domain/graph';
import { completedRunFixture } from '../src/test/completed-run';

test('projects known execution stages and dynamic decisions', () => {
  const { nodes, edges } = buildGraphElements(completedRunFixture.state);

  expect(nodes.map((node) => node.id)).toEqual(
    expect.arrayContaining(['collect', 'validate', 'predict', 'simulate', 'critique', 'explain']),
  );
  expect(edges.some((edge) => edge.source === 'simulate' && edge.target === 'simulate_more')).toBe(true);
  expect(edges.some((edge) => edge.source === 'simulate_more' && edge.target === 'critique')).toBe(true);
});
