import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TrendingUp } from 'lucide-react'
import { StatCard } from './StatCard'

describe('StatCard', () => {
  it('renders the label and value', () => {
    render(<StatCard label="Overall attendance rate" value="87%" icon={TrendingUp} />)

    expect(screen.getByText('Overall attendance rate')).toBeInTheDocument()
    expect(screen.getByText('87%')).toBeInTheDocument()
  })
})
