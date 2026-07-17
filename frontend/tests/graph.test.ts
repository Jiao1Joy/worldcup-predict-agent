import { buildGraphElements } from '../src/domain/graph';
import { completedRunFixture } from '../src/test/completed-run';

test('projects known execution stages and only materialized dynamic decisions', () => {
  const { nodes, edges } = buildGraphElements(completedRunFixture.state);

  expect(nodes.map((node) => node.id)).toEqual(
    expect.arrayContaining(['collect', 'validate', 'predict', 'simulate', 'critique', 'explain']),
  );
  expect(nodes.some((node) => node.id === 'simulate_more')).toBe(false);
  expect(edges.some((edge) => edge.source === 'simulate' && edge.target === 'critique')).toBe(true);
});
