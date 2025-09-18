import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import React from 'react'
import { AppImpl } from '../App'
import { ToastProvider } from '../components/ToastProvider'

describe('App', () => {
  it('renders without crashing', () => {
    const root = document.createElement('div')
    root.id = 'root'
    document.body.appendChild(root)
    render(
      <ToastProvider>
        <AppImpl />
      </ToastProvider>,
      { container: root }
    )
    expect(document.querySelector('#root')).toBeTruthy()
  })
})
